CHEETAH = cheetah
export PYTHONPATH = /home/jmleen/lib/python2.4/site-packages

all: templates/photopage.py templates/browse.py templates/whatsnewpage.py

full: clean all

clean:
	-rm templates/photopage.py templates/browse.py templates/whatsnewpage.py

%.py: %.tmpl
	$(CHEETAH) compile $<
