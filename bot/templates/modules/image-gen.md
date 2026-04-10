## Image Generation

Generate images using the Gemini API:
```bash
python -m bot.features.image_gen "prompt" /data/uploads/output.png
```

Use matplotlib for charts:
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.savefig('/data/uploads/chart.png', dpi=150, bbox_inches='tight')
```

Always mention the full `/data/...` path in your response — it triggers auto-delivery to Telegram.
