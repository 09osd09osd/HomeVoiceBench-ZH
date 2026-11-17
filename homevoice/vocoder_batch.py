"""Bound waveform decoder memory without changing global codec padding."""
def decode_in_chunks(original, encoded, batch_size, pad_codes, trace=None):
    if not isinstance(encoded, list) or not encoded or batch_size < 1:
        raise ValueError('Expected nonempty codec item list and positive batch size')
    maximum = max(len(x['audio_codes']) for x in encoded)
    padded = [{**x, 'audio_codes': pad_codes(x['audio_codes'], maximum)} for x in encoded]
    waves = []
    sample_rate = None
    for start in range(0, len(padded), batch_size):
        items = padded[start:start + batch_size]
        part, rate = original(items)
        if len(part) != len(items):
            raise ValueError('Vocoder output count mismatch')
        if sample_rate is not None and sample_rate != rate:
            raise ValueError('Vocoder sample rate changed within batch')
        sample_rate = rate
        waves.extend(part)
        if trace is not None:
            trace.append({'sample_indices': list(range(start, start + len(items))),
                          'batch_size': len(items), 'padded_codec_frames': maximum})
    return waves, sample_rate
