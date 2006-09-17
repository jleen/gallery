CHEETAH = cheetah
export PYTHONPATH = /home/jmleen/lib/python2.4/site-packages

TARGETS = photopage.py browse.py whatsnewpage.py
all: $(TARGETS)

full: clean all

clean:
	-rm $(TARGETS)

%.py: %.tmpl
	$(CHEETAH) compile $<
