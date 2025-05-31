Title: Testing USD hooks outside of Blender
Description: The Blender API exposes third-party Python modules

Part of our pipeline is automated through a Blender extension that pre / post process USD with USDHooks. For a long time, our integration tests had to actually run the Blender executable: we had to import the USD modules, and those were not available through the pip installable `bpy` module. Installing `usd-core` alongside `bpy` wouldn't work: we would have two USD libraries running into the same process (one from `usd-core`, the other from `bpy`) and that's a recipe for disater.

Thankfully, since Blender 4.4, the function [`bpy.expose_bundled_modules()`](https://developer.blender.org/docs/release_notes/4.4/python_api/#blender-as-a-python-module) makes the third-party bundled modules, notably USD, available from the rest of the application.

```python
import unittest
import bpy

bpy.
```

