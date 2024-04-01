# jackdaw
So far, this project has just been a sandbox to rough in some ideas. The loop in
main.py waits for an input audio (a person querying the language model), and 
then when one is supplied, it is sent to OpenAI's whisper model to generate a 
transcription and the input audio is deleted. 

The transcription is saved as a text file and is soon discovered by the loop, 
which then sends the transcription to a language model to generate a response. 

The response is then received and saved to a new input text file as the 
transcription file is deleted. 

The new text file, representing the language model's response, is then 
discovered and submitted to MaryTTS, running on another host. 

The audio file generated by MaryTTS is then sent back to the original server but 
is not yet suitable for playback. At this point, the sox program is invoked from 
the command line to convert the audio to stereo, 32-bit, 2-channel WAV format, 
and the original audio is deleted, along with the language model's text 
response. 

The final audio output, representing the language model's voice response to the 
original query, is then played on the JACK bus with a JACK client that is 
instantiated by the loop in main.py. When the playback is finished, the JACK 
client melts away and the audio file is deleted. The loop then waits for the 
next query.

### Requirements
JACK2 -- The JACK server must be running on the host machine. TortoiseTTS would 
of course be the preferred solution for the output audio, but my older machines 
struggle to run it and my Wintendo machine can run it, but I'm not interested in 
the Windows ecosystem outside of gaming. 

JackTrip -- JackTrip is not used directly in this code, but it is used to 
connect all of the PCs on the network already running JACK. High-quality, multi-
channel audio can be sent selectively between the PCs on the network with very 
low latency. PCs connected with JackTrip and running JACK are able to process 
audio in real-time.

MaryTTS -- MaryTTS sits in that weird place that is not entirely unpleasant, but 
definitely does not sound like a human. I don't know whether anyone would want 
to hear an entire audiobook in that voice, but it suits as a voice for the house 
computer everywhere all at once on the JACK bus, running on connected PCs.

OpenAI Whisper -- OpenAI's Whisper does such a great job of transcribing 
punctuation that MaryTTS is really given it's best chance to shine. 

SOX -- SOX is used to convert the audio file from MaryTTS to a format that JACK
can play.