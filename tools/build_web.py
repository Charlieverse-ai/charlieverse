import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def build() -> None:
    subprocess.run(["npm", "ci"], check=True, cwd="web")
    subprocess.run(["npm", "run", "build"], check=True, cwd="web")


class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build()


if __name__ == "__main__":
    build()
