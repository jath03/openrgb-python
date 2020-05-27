import setuptools
import os

with open("README.md", "r") as f:
    long_description = f.read()

print(os.environ.get('OPENRGB_PACKAGE_VERSION'))

setuptools.setup(
    name="openrgb-python",
    version='0.0.1,'#os.environ['OPENRGB_PACKAGE_VERSION'].strip("v\'\""),
    author="jath03",
    description="A python client for the OpenRGB SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jath03/openrgb-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
