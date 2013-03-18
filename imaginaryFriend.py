#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk

import gobject
import pygst
pygst.require('0.10')
gobject.threads_init()
import gst

import cleverbot
import pygame
import urllib2
import os

class imaginaryFriend(object):
	"""Vocally-enhanced Cleverbot Session"""
	def __init__(self):
		"""Initialize app"""
		self.init_gui()
		self.init_gst()
		self.cb = cleverbot.Session()

	def init_gui(self):
		"""Initialize the GUI components"""
		self.window = gtk.Window()
		self.window.connect("delete-event", gtk.main_quit)
		self.window.set_default_size(400,200)
		self.window.set_border_width(10)
		vbox = gtk.VBox()
		self.textbuf = gtk.TextBuffer()
		self.text = gtk.TextView(self.textbuf)
		self.text.set_wrap_mode(gtk.WRAP_WORD)
		vbox.pack_start(self.text)
		self.button = gtk.ToggleButton("Ask")
		self.button.connect('clicked', self.button_clicked)
		vbox.pack_start(self.button, False, False, 5)
		self.window.add(vbox)
		self.window.show_all()

	def init_gst(self):
		"""Initialize the speech components"""
		self.pipeline = gst.parse_launch('gconfaudiosrc ! audioconvert ! audioresample '
		                                 + '! vader name=vad auto-threshold=true '
		                                 + '! pocketsphinx name=asr ! fakesink')
		asr = self.pipeline.get_by_name('asr')
		asr.connect('partial_result', self.asr_partial_result)
		asr.connect('result', self.asr_result)
		asr.set_property('configured', True)

		bus = self.pipeline.get_bus()
		bus.add_signal_watch()
		bus.connect('message::application', self.application_message)

		self.pipeline.set_state(gst.STATE_PAUSED)

	def asr_partial_result(self, asr, text, uttid):
		"""Forward partial result signals on the bus to the main thread."""
		struct = gst.Structure('partial_result')
		struct.set_value('hyp', text)
		struct.set_value('uttid', uttid)
		asr.post_message(gst.message_new_application(asr, struct))

	def asr_result(self, asr, text, uttid):
		"""Forward result signals on the bus to the main thread."""
		struct = gst.Structure('result')
		struct.set_value('hyp', text)
		struct.set_value('uttid', uttid)
		asr.post_message(gst.message_new_application(asr, struct))

	def application_message(self, bus, msg):
		"""Receive application messages from the bus."""
		msgtype = msg.structure.get_name()
		if msgtype == 'partial_result':
		    self.partial_result(msg.structure['hyp'], msg.structure['uttid'])
		elif msgtype == 'result':
		    self.final_result(msg.structure['hyp'], msg.structure['uttid'])
		    self.pipeline.set_state(gst.STATE_PAUSED)
		    self.button.set_active(False)
		    self.ask_cleverbot(msg.structure['hyp'])

	def partial_result(self, hyp, uttid):
		"""Delete any previous selection, insert text and select it."""
		# All this stuff appears as one single action
		self.textbuf.begin_user_action()
		self.textbuf.delete_selection(True, self.text.get_editable())
		self.textbuf.insert_at_cursor(hyp)
		ins = self.textbuf.get_insert()
		iter = self.textbuf.get_iter_at_mark(ins)
		iter.backward_chars(len(hyp))
		self.textbuf.move_mark(ins, iter)
		self.textbuf.end_user_action()

	def final_result(self, hyp, uttid):
		"""Insert the final result."""
		# All this stuff appears as one single action
		self.textbuf.begin_user_action()
		self.textbuf.delete_selection(True, self.text.get_editable())
		mytag = self.textbuf.create_tag(name=None, foreground='blue')
		self.textbuf.insert_with_tags(self.textbuf.get_end_iter(), 'ME: '+hyp+'.\n', mytag)
		self.textbuf.end_user_action()
				
		
	def ask_cleverbot(self, text):
		"""Send input text to Cleverbot and fetch response """
		response = self.cb.Ask(text)
		self.textbuf.begin_user_action()
		cbtag = self.textbuf.create_tag(name=None, foreground='red')
		self.textbuf.insert_with_tags(self.textbuf.get_end_iter(), 'CB: '+response+'\n', cbtag)
		self.textbuf.end_user_action()
		self.talk(response)
		
	def talk(self, text):
		"""Convert response text to audio using Google Translate API"""
		url = 'http://translate.google.com/translate_tts'
		mp3 = 'speech_google.mp3'
		opener = urllib2.build_opener()
		opener.addheaders = [('User-agent', 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)')]
		response = opener.open(url+'?q='+text.replace(' ','%20')+'&tl=en')
		ofp = open(mp3, 'wb')
		ofp.write(response.read())
		ofp.close()		
		self.play_mp3(os.path.join(os.getcwd(), mp3))
	
	def play_mp3(self, music_file):
		"""Play audio file"""
		pygame.init()
		clock = pygame.time.Clock()
		pygame.mixer.music.load(music_file)
		pygame.mixer.music.play()
		while pygame.mixer.music.get_busy():
			#check if playback has finished
			clock.tick(5)
		#pygame.quit()

	def button_clicked(self, button):
		"""Handle button presses."""
		if button.get_active():
		    button.set_label("Listening...")
		    self.pipeline.set_state(gst.STATE_PLAYING)
		else:
		    button.set_label("Ask")
		    vader = self.pipeline.get_by_name('vad')
		    vader.set_property('silent', True)

app = imaginaryFriend()
gtk.main()