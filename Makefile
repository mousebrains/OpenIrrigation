install:
	$(MAKE) -C package
	$(MAKE) -C database
	$(MAKE) -C scripts
	$(MAKE) -C public_html
	$(MAKE) -C service
