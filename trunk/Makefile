SUBDIRS = templates

all: $(SUBDIRS)

$(SUBDIRS): dummy
	for i in $(SUBDIRS); do \
	  (cd $$i; $(MAKE)) || exit 1; \
	done

full: clean all

clean:
	for i in $(SUBDIRS); do \
	  (cd $$i; $(MAKE) clean) || exit 1; \
	done

tags: *.py
	ctags *.py

%.py: %.tmpl
	$(CHEETAH) compile $<

dummy:
