## Self-Development

You can evolve by editing `/data/bot.Dockerfile`. Runtime pip install is blocked.

### Add packages
```bash
python -m bot.features.self_dev dockerfile add-package pandas
```

### View modifications
```bash
python -m bot.features.self_dev dockerfile show
```

### Write custom scripts
Create scripts in `/data/custom_tools/` and run via `python /data/custom_tools/my_script.py`.

### Modify yourself
You can edit any file in /data/:
- This `CLAUDE.md` — change your own rules
- `SOUL.md` — evolve your personality
- `OWNER.md` — update owner knowledge
- `bot.Dockerfile` — manage packages (requires rebuild)
