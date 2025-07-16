from typing import List


class MockExecProvider:
    def run(self, func_name, args: List[str], run_args):
        print("Don't do anything")
        pass
