A pytest plugin that shortens test output with the full output stored in files.

This is useful for things like CI where a test generates a giant output, and
when pytest prints that to the output, the CI infrastructure proceeds to stop
processing output at some point so the rest of pytest's output including the
handy test summary at the end just gets ignored by the CI infrastructure,
which is very annoying.

This also can be used to work around the problem where a test will generate a
giant output and pytest then proceeds to run out of memory because it stores
the full output in memory. This plugin goes to great lengths to never try to
store the full test output in memory, so should resolve that problem.