static const int BAUD_RATE = 9600;

void check_baud_rate();
void echo();

void setup() {
	Serial.begin(BAUD_RATE);

	while (!Serial) {
	    ; // wait for serial port to connect. Needed for native USB port only
    }
}

void loop() {
	if (Serial.available()) {
		char command = Serial.read();

		switch (command) {
			case 'b':
				check_baud_rate();
				break;
			case 'e':
				echo();
				break;
			default:
				Serial.println(".");
		}
	}
}

void check_baud_rate() {
	Serial.println(BAUD_RATE);
}

void echo() {
    String s = Serial.readStringUntil('\n');

	Serial.println(s);
}
