from contextlib import ExitStack

class ContextManagers:
    def __init__(self, managers):
        self.managers = managers
        self.stack = ExitStack()

    def __enter__(self):
        return [self.stack.enter_context(m) for m in self.managers]

    def __exit__(self, *args):
        return self.stack.__exit__(*args)
