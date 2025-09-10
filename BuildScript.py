
import os 
import PyInstaller.__main__

# locating spec file
workdir = os.getcwd()
fn_msi_spec = os.path.join(workdir, 'Fingerprint_application_win.spec')

# define the "dev\dist" and "dev\build" dirs
devdir = os.getcwd()
distdir = os.path.join(devdir, 'dist')
builddir = os.path.join(devdir, 'build')

PyInstaller.__main__.run(['--distpath', distdir, '--workpath', builddir, fn_msi_spec])