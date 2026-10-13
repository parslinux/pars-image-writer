#!/usr/bin/env python3
import os
import subprocess

from setuptools import setup, find_packages

changelog = "debian/changelog"
version = "1.0.0"
if os.path.exists(changelog):
    head = open(changelog).readline()
    try:
        version = head.split("(")[1].split(")")[0]
    except:
        print("debian/changelog format is wrong for get version")
    f = open("src/__version__", "w")
    f.write(version)
    f.close()


def create_mo_files():
    podir = "po"
    mo = []
    for po in os.listdir(podir):
        if po.endswith(".po"):
            lang = po.split(".po")[0]
            os.makedirs(
                "{}/{}/LC_MESSAGES".format(podir, lang), exist_ok=True
            )
            mo_file = "{}/{}/LC_MESSAGES/{}.mo".format(podir, lang, "pars-image-writer")
            msgfmt_cmd = "msgfmt {} -o {}".format(podir + "/" + po, mo_file)
            subprocess.call(msgfmt_cmd, shell=True)
            mo.append(
                (
                    "/usr/share/locale/" + lang + "/LC_MESSAGES",
                    [mo_file],
                )
            )
    return mo


data_files = [
    ("/usr/share/applications/", ["tr.org.pars.image-writer.desktop"]),
    (
        "/usr/share/pars/pars-image-writer/assets",
        [
            "assets/main.svg",
            "assets/iso.svg",
            "assets/disk.svg",
            "assets/pars-image-writer.svg",
            "assets/uefi-ntfs.img",
        ],
    ),
    (
        "/usr/share/pars/pars-image-writer/src",
        [
            "src/Main.py",
            "src/MainWindow.py",
            "src/ModernWindow.py",
            "src/CLI.py",
            "src/ISOCopier.py",
            "src/ImageWriter.py",
            "src/USBDeviceManager.py",
            "src/Utils.py",
            "src/Catalog.py",
            "src/NetbootServer.py",
            "src/copy_dir_with_dd.sh",
            "src/__version__",
        ],
    ),
    ("/usr/share/pars/pars-image-writer/ui", ["ui/MainWindow.glade"]),
    (
        "/usr/share/polkit-1/actions",
        ["tr.org.pars.pkexec.pars-image-writer.policy"],
    ),
    ("/usr/bin/", ["pars-image-writer", "pars-image-writer-cli", "pars-image-writer-gtk4"]),
    (
        "/usr/share/icons/hicolor/scalable/apps/",
        ["assets/pars-image-writer.svg"],
    ),
    (
        "/usr/share/metainfo",
        ["tr.org.pars.ImageWriter.metainfo.xml"],
    ),
] + create_mo_files()

setup(
    name="Pars Image Writer",
    version=version,
    packages=find_packages(),
    scripts=["pars-image-writer", "pars-image-writer-cli", "pars-image-writer-gtk4"],
    install_requires=["PyGObject"],
    data_files=data_files,
    author="Pars Developers",
    author_email="dev@pars.org.tr",
    description="Pars ISO & IMG Image Writer.",
    license="GPLv3",
    keywords="iso usb image burn write pars",
    url="https://github.com/parslinux/pars-image-writer",
)
