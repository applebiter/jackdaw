# jackdaw
So far, this project has just been a sandbox to rough in some ideas. The loop in
main.py waits for an input audio (a person querying the language model), and 
then when one is supplied, it is sent to OpenAI's whisper model to generate a 
transcription and the input audio is deleted. The transcription is saved as a 
text file and is soon discovered by the loop, which then sends the transcription 
to a language model to generate a response. The response is then received and 
saved to a new input text file as the transcription file is deleted. The new 
text file, representing the language model's response, is then discovered and 
submitted to MaryTTS, running on another server. The audio file generated by
MaryTTS is then sent back to the original server but it is not yet suitable for
playback. At this point, the sox program is invoked from the command line to 
convert the audio to stereo, 32-bit, 2-channel WAV format, and the original 
audio is deleted, along with the language model's text response. The final audio 
output, representing the language model's voice response to the original query, 
is then played on the JACK bus with a JACK client that is instantiated by the 
loop in main.py. When the playback is finished, the JACK client melts away and 
the audio file is deleted. The loop then waits for the next query.