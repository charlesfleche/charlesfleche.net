Title: Testing USD hooks outside of Blender
Description: The Blender API exposes third-party Python modules

Part of our pipeline is automated through a [Blender](https://blender.org) extension that pre / post process [USD](https://openusd.org) with [USDHooks](https://docs.blender.org/api/current/bpy.types.USDHook.html). For a long time, our integration tests had to actually run the Blender executable: we had to import the USD modules, and those were not available through the pip installable [`bpy`](https://pypi.org/project/bpy/) module. Installing [`usd-core`](https://pypi.org/project/usd-core/) alongside `bpy` wouldn't work: we would have two USD libraries running into the same process (one from `usd-core`, the other from `bpy`) and that's a recipe for disater.

Thankfully, since Blender 4.4, the function [`bpy.expose_bundled_modules()`](https://developer.blender.org/docs/release_notes/4.4/python_api/#blender-as-a-python-module) makes the third-party bundled modules, notably USD, available from the rest of the application.

```python
import unittest

import bpy

bpy.expose_bundled_modules()

from pxr import Usd

class MyTest(unittest.TestCase):
    ...
```

Thanks to `bpy.expose_bundled_modules()` we can now run our tests fully from a Python interpreter, without running the Blender executable:
- as we stay fully in the Python world, the setup is the same on local Windows workstation and Linux CI machines
- we can simply run and debug our tests from the native IDEs integrations

