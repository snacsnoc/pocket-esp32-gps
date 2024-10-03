PORT ?= tty.usbserial-0001
MPFSHELL = mpfshell
SRC_DIR = src

.PHONY: all flash clean

all: flash

flash:
	@echo "Flashing files to ESP32..."
	@$(MPFSHELL) -n -c "\
		open $(PORT); \
		md /lib; \
		md /handlers; \
		md /utils; \
		mput $(SRC_DIR)/*.py /; \
		mput $(SRC_DIR)/lib/*.py /lib/; \
		mput $(SRC_DIR)/handlers/*.py /handlers/; \
		mput $(SRC_DIR)/utils/*.py /utils/; \
		ls -r /; \
		exec import machine; machine.soft_reset()"
	@echo "Flash complete and device reset."

clean:
	@echo "Cleaning ESP32 filesystem..."
	@$(MPFSHELL) -n -c "open $(PORT); mrm /*"
	@echo "Clean complete."