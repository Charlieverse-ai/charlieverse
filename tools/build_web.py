import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        subprocess.run(["npm", "ci"], check=True, cwd="web")
        subprocess.run(["npm", "run", "build"], check=True, cwd="web")
