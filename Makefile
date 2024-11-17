PORT = tty.usbserial-0001
MPFSHELL = mpfshell
SRC_DIR = src

.PHONY: all flash clean debug

all: flash

flash:
	@echo "Flashing files to ESP32..."
	@$(MPFSHELL) -n -c "\
		open $(PORT); \
		lcd src/; \
		cd /; md lib; md handlers; md utils; \
		mput .*\.py; \
		cd /lib; lcd lib/; \
		mput .*\.py; \
		cd /handlers; lcd ../handlers/; \
		mput .*\.py; \
		cd /utils; lcd ../utils/; \
		mput .*\.py; \
		exec import machine; exec machine.reset();"\
	|| (echo "Error: mpfshell command failed"; exit 1)
	@echo "Flash complete and device reset."

flash-handlers:
	@echo "Flashing files to ESP32..."
	@$(MPFSHELL) -n -c "\
		open $(PORT); \
		lcd src/; \
		cd /handlers; lcd handlers/; \
		mput .*\.py; \
		exec import machine; exec machine.reset();" \
	|| (echo "Error: mpfshell command failed"; exit 1)
	@echo "Flash complete and device reset."


clean:
	@echo "Cleaning up all files from the ESP32..."
	@$(MPFSHELL) -n -c "\
		open $(PORT); \
		cd /; mrm .*\\.py; rm user_settings.json; \
		cd /lib; mrm .*\\.py; \
		cd /handlers; mrm .*\\.py; \
		cd /utils; mrm .*\\.py" \
	|| (echo "Error: mpfshell command failed"; exit 1)
	@echo "Cleanup complete!"




flash-debug:
	@echo "Flashing files to ESP32 (debug mode)..."
	@$(MPFSHELL) -n -c "\
		open $(PORT); \
		lcd src/; \
		cd /; md lib; md handlers; md utils; \
		mput .*\\.py; \
		cd /lib; lcd lib/; \
		mput .*\\.py; \
		cd /handlers; lcd ../handlers/; \
		mput .*\\.py; \
		cd /utils; lcd ../utils/; \
		mput .*\\.py" 2>&1 | tee flash_debug.log \
	|| (echo "Error: mpfshell command failed"; exit 1)
	@echo "Debug flash complete. Logs saved to flash_debug.log."
