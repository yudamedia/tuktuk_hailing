from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="tuktuk_hailing",
    version="0.0.1",
    description="Ride hailing system for Sunny Tuktuk",
    author="Sunny Tuktuk",
    author_email="info@sunnytuktuk.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
