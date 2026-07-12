from os.path import join

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory


class Pygame2Recipe(CompiledComponentsPythonRecipe):
    """
    Recipe to build apps based on SDL2-based pygame (pygame-ce).

    python-for-android 에는 아직 병합된 pygame-ce 레시피가 없어서(PR kivy/python-for-android#2971
    가 미병합 상태), 그 PR 의 레시피를 로컬로 들고 온다. buildozer.spec 의
    `p4a.local_recipes = ./p4a-recipes` 가 이 폴더를 가리킨다.

    버전은 2.4.0 에 고정한다. pygame-ce 2.5.x 부터는 빌드 시스템이 meson 으로 바뀌어
    아래의 setuptools/Setup 방식과 맞지 않는다(빌드가 깨진다). 2.4.0 은 여전히 pygame-ce 라서
    데스크톱(2.5.7)과 동작이 거의 같고 APP_* 생명주기 이벤트·K_AC_BACK 등을 모두 지원한다.

    .. warning:: Some pygame functionality is still untested, and some
        dependencies like freetype, postmidi and libjpeg are currently
        not part of the build. It's usable, but not complete.
    """

    version = '2.4.0'
    url = 'https://github.com/pygame-community/pygame-ce/archive/{version}.tar.gz'

    site_packages_name = 'pygame-ce'
    name = 'pygame-ce'

    depends = ['sdl2', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'setuptools', 'jpeg', 'png']
    call_hostpython_via_targetpython = False  # Due to setuptools
    install_in_hostpython = False

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            setup_template = open(join("buildconfig", "Setup.Android.SDL2.in")).read()
            env = self.get_recipe_env(arch)
            env['ANDROID_ROOT'] = join(self.ctx.ndk.sysroot, 'usr')

            png = self.get_recipe('png', self.ctx)
            png_lib_dir = join(png.get_build_dir(arch.arch), '.libs')
            png_inc_dir = png.get_build_dir(arch)

            jpeg = self.get_recipe('jpeg', self.ctx)
            jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

            sdl_mixer_includes = ""
            sdl2_mixer_recipe = self.get_recipe('sdl2_mixer', self.ctx)
            for include_dir in sdl2_mixer_recipe.get_include_dirs(arch):
                sdl_mixer_includes += f"-I{include_dir} "

            # SDL2_image 2.6+ 는 헤더(SDL_image.h)를 include/ 하위로 옮겼다. 원본 레시피가 base
            # 경로만 하드코딩해 'SDL_image.h file not found' 로 깨졌다 → mixer 처럼 get_include_dirs
            # (jni/SDL2_image/include 반환)를 쓰고, 안전하게 base 경로도 함께 넘긴다.
            sdl_image_includes = "-I" + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_image') + " "
            sdl2_image_recipe = self.get_recipe('sdl2_image', self.ctx)
            for include_dir in sdl2_image_recipe.get_include_dirs(arch):
                sdl_image_includes += f"-I{include_dir} "

            setup_file = setup_template.format(
                sdl_includes=(
                    " -I" + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include') +
                    " -L" + join(self.ctx.bootstrap.build_dir, "libs", str(arch)) +
                    " -L" + png_lib_dir + " -L" + jpeg_lib_dir + " -L" + arch.ndk_lib_dir_versioned),
                sdl_ttf_includes="-I"+join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_ttf'),
                sdl_image_includes=sdl_image_includes,
                sdl_mixer_includes=sdl_mixer_includes,
                jpeg_includes="-I"+jpeg_inc_dir,
                png_includes="-I"+png_inc_dir,
                freetype_includes=""
            )
            open("Setup", "w").write(setup_file)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['USE_SDL2'] = '1'
        env["PYGAME_CROSS_COMPILE"] = "TRUE"
        env["PYGAME_ANDROID"] = "TRUE"
        return env


recipe = Pygame2Recipe()
