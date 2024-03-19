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

This is all vaporware for the moment as I mess around with speech-to-text 
and text-to-speech solutions. The idea here is to give the LLM agents a voice 
and a way to communicate with each other and with the user. Fortunately, I am 
already familiar with the JACK server and a small subset of its ecosystem. I 
will post changes here as they become interesting.
