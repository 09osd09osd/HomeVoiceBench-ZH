"""Validate real PCM bytes and repair streaming WAV length headers without resampling."""
import hashlib,io,wave
def canonical_wav(data):
    chunks=[]
    with wave.open(io.BytesIO(data),'rb') as w:
        channels=w.getnchannels();width=w.getsampwidth();rate=w.getframerate();declared=w.getnframes()
        if w.getcomptype()!='NONE':raise ValueError('expected uncompressed PCM')
        while chunk:=w.readframes(65536):chunks.append(chunk)
    pcm=b''.join(chunks);stride=channels*width
    if not pcm or len(pcm)%stride:raise ValueError('empty or incomplete PCM frames')
    frames=len(pcm)//stride;duration=frames/rate
    if not .1<=duration<=120:raise ValueError(f'user waveform duration out of range: {duration}')
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(channels);w.setsampwidth(width);w.setframerate(rate);w.writeframes(pcm)
    canonical=out.getvalue()
    with wave.open(io.BytesIO(canonical),'rb') as w:
        if w.readframes(frames)!=pcm or w.getnframes()!=frames:raise ValueError('PCM preservation failed')
    return canonical,{'duration_seconds':duration,'sample_rate':rate,'channels':channels,'codec':f'PCM{width*8}','wav_container':{'version':'canonical_pcm_v1','upstream_sha256':hashlib.sha256(data).hexdigest(),'canonical_sha256':hashlib.sha256(canonical).hexdigest(),'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'upstream_declared_frames':declared,'actual_frames':frames,'header_length_repaired':declared!=frames,'resampled':False,'samples_changed':False}}
