### To clip the video, from time to to time locally using ffmeg

```bash
ffmpeg -i full_walkthrough.mp4 -ss 00:00:30 -to 00:02:30 -c copy clip.mp4
```

### Costs:

Every Video second ≈ 263 tokens of input
Every Audio second ≈ 32 tokens of input
