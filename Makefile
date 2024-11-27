PORT = tty.usbserial-0001
MPFSHELL = mpfshell
MPY_CROSS=mpy-cross
SRC_DIR = src

.PHONY: all flash clean debug

all: flash

# Compile .py files in handlers directory to .mpy
mpy-compile-handlers:
	@echo "Compiling .py files in $(SRC_DIR)/handlers to .mpy..."
	@for file in $(SRC_DIR)/handlers/*.py; do \
		echo "Compiling $$file..."; \
		$(MPY_CROSS) $$file || (echo "Error compiling $$file" && exit 1); \
	done
	@echo "Compilation complete."

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

# Flash compiled .mpy files to the ESP32
mpy-flash-handlers: mpy-compile-handlers
	@echo "Flashing files to ESP32..."
	@$(MPFSHELL) -n -c "\
		open $(PORT); \
		lcd $(HANDLERS_DIR)/; \
		cd /handlers; \
		mput *.mpy; \
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
