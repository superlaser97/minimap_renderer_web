import json
from pathlib import Path
from renderer.render import Renderer
from replay_parser import ReplayParser
from renderer.utils import LOGGER


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=str, required=True)
    parser.add_argument("--anon", action="store_true", help="Anonymize player names")
    parser.add_argument("--no-chat", action="store_true", help="Disable chat")
    parser.add_argument("--no-logs", action="store_true", help="Disable logs (ribbons, damage, etc)")
    parser.add_argument("--team-tracers", action="store_true", help="Enable team tracers")
    parser.add_argument("--fps", type=int, default=20, help="Output FPS")
    parser.add_argument("--quality", type=int, default=7, help="Output quality (0-10)")

    namespace = parser.parse_args()
    path = Path(namespace.replay)
    video_path = path.parent.joinpath(f"{path.stem}.mp4")
    with open(namespace.replay, "rb") as f:
        LOGGER.info("Parsing the replay file...")
        replay_info = ReplayParser(
            f, strict=True, raw_data_output=False
        ).get_info()
        LOGGER.info(f"Replay has version {replay_info['open']['clientVersionFromExe']}")
        LOGGER.info("Rendering the replay file...")
        renderer = Renderer(
            replay_info["hidden"]["replay_data"],
            logs=not namespace.no_logs,
            enable_chat=not namespace.no_chat,
            anon=namespace.anon,
            team_tracers=namespace.team_tracers,
            use_tqdm=True,
        )
        with open(path.parent.joinpath(f"{path.stem}-builds.json"), "w") as fp:
            json.dump(renderer.get_player_build(), fp, indent=4)
        renderer.start(str(video_path), fps=namespace.fps, quality=namespace.quality)
        LOGGER.info(f"The video file is at: {str(video_path)}")
        LOGGER.info("Done.")
