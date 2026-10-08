class Counter:
    value = 0
    def increment(self):
        self.value += 1
    def reset(self):
        Counter.value = 0
