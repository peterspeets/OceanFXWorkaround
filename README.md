# OceanFXWorkaround
Some Ocean FX drivers may have trouble using the onboard memory chip for faster acquisition rates when used in Python. This workaround uses a binary protocol to interface the spectrometer. It requires the libusb USB driver to function. Beware: the code is written for the use in a single experimental setup, and the code style reflects that.

See this thread for the Ocean bug: https://github.com/ap--/python-seabreeze/issues/59
