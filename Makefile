#
# Makefile for cloud-install
#
NAME        = cloud-installer
TOPDIR      := $(shell basename `pwd`)
GIT_REV     := $(shell git log --oneline -n1| cut -d" " -f1)
VERSION     := $(shell perl -nle '/${NAME}\s.(.*)-\dubuntu\d/ && print($1) && exit' debian/changelog)

$(NAME)_$(VERSION).orig.tar.gz: clean
	cd .. && tar czf $(NAME)_$(VERSION).orig.tar.gz $(TOPDIR) --exclude-vcs --exclude=debian

tarball: $(NAME)_$(VERSION).orig.tar.gz

clean:
	@debian/rules clean
	@rm -rf debian/cloud-install

deb-src: clean update_version tarball
	wrap-and-sort
	@debuild -S -us -uc

deb: clean update_version tarball
	wrap-and-sort
	@debuild -us -uc -i

current_version:
	@echo $(VERSION)

git_rev:
	@echo $(GIT_REV)

update_version:
	@sed -i -r "s/(^__version__\s=\s)(.*)/\1$(VERSION)/" cloudinstall/__init__.py

status:
	PYTHONPATH=$(shell pwd):$(PYTHONPATH) bin/cloud-status

all: deb
