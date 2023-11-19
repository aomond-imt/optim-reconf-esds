from execo_engine import ParamSweeper
import os

sweeper_path = f"{os.environ['HOME']}/optim-esds-sweeper"
if os.path.exists(sweeper_path) and os.path.getsize(f"{sweeper_path}/sweeps") > 0:
    sweeper = ParamSweeper(sweeper_path)
    print(sweeper)
else:
    print(f"No experiment done")
