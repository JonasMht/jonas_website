
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

.PHONY: push_quit
push_quit:
	make push
	-shutdown 0

.PHONY: pull
pull:
	git pull origin main
