
DES = # Description

ifndef DES
DES = Automatic commit & push
endif

DATE := $(shell date +"%d.%m.%Y at %H:%M:%S")

all: push


.PHONY: run
run:
	hugo serve

.PHONY: push
push:
	-git add .
	-git commit -a -m "$(DES), $(DATE)"
	-git push

# Setup on ubuntu
.PHONY: setup
setup:
	sudo snap install hugo
	sudo snap install go --classic

.PHONY: push_quit
push_quit:
	make push
	-shutdown 0

.PHONY: pull
pull:
	git pull

.PHONY: update
update:
	echo "See documentation for more information"
	hugo mod get -u github.com/CaiJimmy/hugo-theme-stack/v3
	hugo mod tidy