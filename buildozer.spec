[app]
# (str) Title of your application
title = 몽중농원

# (str) Package name
package.name = dreamfarm

# (str) Package domain
package.domain = mongjung.nongwon

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,ttf

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,pygame-ce,numpy==1.24.3

# (str) Application versioning (method 1)
version = 2.2.2

# (list) Supported orientations
# Valid values are: landscape, portrait, portrait-upsidedown, landscape-left, landscape-right
orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Target API your APK will support.
android.api = 33

# (list) Supported architectures
android.archs = arm64-v8a, armeabi-v7a

# (bool) Use private storage for data (set to True for default behaviour)
android.private_storage = True

# (str) Android NDK version to use
android.ndk = 25b

# (str) python-for-android branch to use
p4a.branch = develop

# (str) Android NDK directory (if empty, it will be automatically downloaded)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded)
#android.ant_path =

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
