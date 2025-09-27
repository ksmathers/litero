import argparse
import os
import re
import sys
from pathlib import Path
from typing import List

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:
    BeautifulSoup = None  # type: ignore

import torch
from kokoro import KPipeline

try:
    from pydub import AudioSegment  # type: ignore
except ImportError:
    AudioSegment = None  # type: ignore


def html_to_tts_chunks(html_string: str) -> List[str]:
    """Convert HTML string to TTS (Text-to-Speech) chunks.
    This method processes an HTML document and converts it into
    text, one sentence per chunk.  After each paragraph a 
    marker string "[break=medium]" is added to indicate a medium 
    break duration.

    Maps common HTML elements to their StyleTTS2 equivalents:
    - <em>, <i> -> '[excited]'
    - <strong>, <b> -> '[excited]'
    - <p> -> ends the chunk and adds '[break=medium]' between paragraphs
    - <br> -> ends the chunk and adds '[break=small]' between lines
    - <h1>-<h6> -> Adds '[cinematic]' before, and '[break=medium]' after headings
    - <div> -> adds '[break=small]' between divs
    - <span> -> preserved as text content
    - Removes script, style, and other non-speech elements
    
    Args:
        html_string: The HTML content as a string
        
    Returns:
        TTS formatted List[str]
    """
    tts_chunks: List[str] = []
    if not BeautifulSoup:
        raise RuntimeError("BeautifulSoup is required for HTML parsing.")
    else:
        # Use BeautifulSoup for better parsing
        soup = BeautifulSoup(html_string, "html.parser")
        
        # Remove script, style, and other non-speech elements
        for tag in soup(["script", "style", "noscript", "meta", "link", "title"]):
            tag.decompose()
        
        # Process elements in document order
        for element in soup.descendants:
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                # Add cinematic marker before heading
                cinematic_tag = soup.new_string("[cinematic]")
                element.insert_before(cinematic_tag)
                # Add break after heading
                break_tag = soup.new_string("[break=medium]")
                element.insert_after(break_tag)
                
            elif element.name in ["em", "i", "strong", "b"]:
                # Add excited marker before emphasis
                #excited_tag = soup.new_string("[excited]")
                element.replace_with(f"[{element.get_text()}](+8)")
                
            elif element.name == "br":
                element.replace_with("[break=small]")
                
            elif element.name == "p":
                # Add break after paragraph
                break_tag = soup.new_string("[break=small]")
                element.insert_after(break_tag)
                
            elif element.name == "div":
                # Add small break after div
                break_tag = soup.new_string("[break=small]")
                element.insert_after(break_tag)
        
        # Get text content
        text = soup.get_text()
        
        # Clean up and split into chunks
        # Split by break markers and sentence boundaries
        parts = re.split(r"(\[break=[^]]+\]|\[cinematic\]|\[excited\])", text)
        current_chunk = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if part.startswith("[") and part.endswith("]"):
                # Handle special markers
                if part.startswith("[break="):
                    # Add current chunk if it has content
                    if current_chunk.strip():
                        tts_chunks.append(current_chunk.strip())
                        current_chunk = ""
                    # Add the break marker as a separate chunk
                    tts_chunks.append(part)
                else:
                    # Style markers like [cinematic] or [excited] get added to current chunk
                    if current_chunk:
                        current_chunk += part
                    else:
                        current_chunk = part
            else:
                # Regular text - split into sentences
                sentences = re.split(r"(?<=[.!?])\s+", part)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        if current_chunk:
                            current_chunk += " " + sentence
                        else:
                            current_chunk = sentence
                        
                        # Check if sentence ends with punctuation, create chunk
                        if re.search(r"[.!?]$", sentence):
                            tts_chunks.append(current_chunk.strip())
                            tts_chunks.append("[break=tiny]")
                            current_chunk = ""
        
        # Add any remaining text
        if current_chunk.strip():
            tts_chunks.append(current_chunk.strip())
    
    # Clean up whitespace in chunks and remove empty chunks
    tts_chunks = [re.sub(r"\s+", " ", chunk).strip() for chunk in tts_chunks if chunk.strip()]
    
    return tts_chunks

silence_audio = torch.zeros(24000, dtype=torch.float32)  # 1 second of silence at 24kHz

def synthesize(chunks: List[str], voice: str, speed: float, device: str | None) -> torch.Tensor:
    pipeline = KPipeline(lang_code='a', device=device)
    audio_segments: List[torch.Tensor] = []
    break_time = 0
    for idx, chunk in enumerate(chunks, 1):
        print(f"[TTS] Synthesizing chunk {idx}/{len(chunks)} (len={len(chunk)})")
        if idx > 100: break # testing

        # Handle special break markers
        if chunk.startswith("[break="):
            # Handle break markers as silent audio
            match = re.match(r"\[break=(tiny|small|medium|large)\]", chunk)
            if match:
                duration_map = {'tiny': 0.1, 'small': 0.3, 'medium': 0.6, 'large': 1.0}
                duration = duration_map.get(match.group(1), 0.5)
                if break_time >= 0:
                    # collapse multiple breaks to just the longest
                    duration -= break_time
                    break_time = duration
                    if duration <= 0:
                        continue
                sr = 24000  # Kokoro sample rate
                num_silent_samples = int(sr * duration)
                audio_segments.append(silence_audio[:num_silent_samples])
            continue

        if chunk.startswith("[cinematic]"):
            chunk = chunk.replace("[cinematic]", "").strip()
            # Apply cinematic effects (e.g., reverb)
            for _, _, audio in pipeline(chunk, voice="am_michael", speed=speed): #, effects=["reverb"]):
                if audio is not None:
                    audio_segments.append(audio.detach().cpu().float())
            continue

        if chunk.startswith("[excited]"):
            chunk = chunk.replace("[excited]", "").strip()
            # Apply excited style (e.g., higher pitch)
            for _, _, audio in pipeline(chunk, voice=voice, speed=speed*1.2): #, effects=["pitch=1.2"]):
                if audio is not None:
                    audio_segments.append(audio.detach().cpu().float())
            continue

        break_time = 0
        # Synthesize speech for the chunk
        for _, _, audio in pipeline(chunk, voice=voice, speed=speed):
            if audio is not None:
                # Ensure 1-D CPU float32 tensor
                audio_segments.append(audio.detach().cpu().float())
    if not audio_segments:
        raise RuntimeError("No audio generated.")
    audio_full = torch.cat(audio_segments)
    # Normalize to prevent clipping
    peak = audio_full.abs().max().item()
    if peak > 0:
        audio_full = audio_full / peak * 0.95
    return audio_full

def save_mp4(waveform: torch.Tensor, out_path: Path, audio_book: bool = True):
    sr = 24000  # Kokoro sample rate
    if AudioSegment is None:
        raise RuntimeError("pydub is required for saving MP4 files.")
    # Use pydub + ffmpeg    
    samples = (waveform.clamp(-1,1) * 32767).short().numpy()
    seg = AudioSegment(
        samples.tobytes(),
        frame_rate=sr,
        sample_width=2,
        channels=1,

    )
    seg.export(str(out_path), format='mp4', bitrate='64k')
    print(f"Saved MP4: {out_path}")


def parse_args():
    p = argparse.ArgumentParser(description="Convert HTML text content to speech MP4 via Kokoro")
    p.add_argument('html_file', type=Path, help='Input HTML file')
    p.add_argument('--voice', default='af_bella', help='Voice name (default: af_bella)')
    p.add_argument('--speed', type=float, default=1.0, help='Speech speed multiplier')
    p.add_argument('--device', default=None, help='Torch device (cpu, mps, cuda)')
    p.add_argument('--max-chars', type=int, default=400, help='Max chars per synthesis chunk')
    p.add_argument('--output', type=Path, help='Explicit output mp3 path (optional)')
    return p.parse_args()

def process_html_file(html_file: Path, voice: str, speed: float, device: str | None, output: Path | None):
    if not html_file.exists():
        print(f"File not found: {html_file}", file=sys.stderr)
        sys.exit(1)
    with open(html_file, 'r', encoding='utf-8') as f:
        html_doc = f.read()
    chunks = html_to_tts_chunks(html_doc)
    if len(chunks) == 0:
        print("No text extracted from HTML.", file=sys.stderr)
        sys.exit(2)
    print(f"Split into {len(chunks)} chunks")
    waveform = synthesize(chunks, voice=voice, speed=speed, device=device)
    if output and os.path.isdir(output):
        out_path = os.path.join(output, html_file.stem + '.m4b')
    else:
        out_path = output if output else html_file.with_suffix('.m4b')
    save_mp4(waveform, out_path)

def main():
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    args = parse_args()
    output = args.output
    if os.path.isdir(args.html_file):
        filelist = list(args.html_file.glob("*.html"))
        for html_file in filelist:
            print(f"Processing {html_file}...")
            if not output:
                output = os.path.join(os.path.dirname(args.html_file), "audio")
                os.makedirs(output, exist_ok=True)
            process_html_file(html_file, args.voice, args.speed, args.device, output)
    else:
        process_html_file(args.html_file, args.voice, args.speed, args.device, output)

if __name__ == '__main__':
    main()
