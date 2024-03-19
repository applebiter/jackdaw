# jackdaw
As far as I know, the JACK library is still the best fit for my use case, which 
is a low-latency audio solution for connecting different LLM agents, possible 
each hosted on separate machines. The JACK server itself provides a bus for 
audio and MIDI data, and the jacktrip application connects multiple machines 
over the local network and/or the internet. The JACK library for Python is 
called JACK-Client, and it is available on PyPI. The JACK-Client library is a 
wrapper around the C API of the JACK library. The JACK-Client library is not a 
complete wrapper around the C API of the JACK library, but it is enough for my 
use case.
