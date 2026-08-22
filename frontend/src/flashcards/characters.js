import boltImg from './characters/bolt.png';
import zaraImg from './characters/zara.png';
import novaImg from './characters/nova.png';
import beepImg from './characters/beep.png';
import echoImg from './characters/echo.png';
import miraImg from './characters/mira.png';

export const CHARACTERS = {
  BOLT: {
    id: "BOLT",
    name: "BOLT",
    tagline: "Brave space robot from the future",
    tagline_hindi: "भविष्य का बहादुर अंतरिक्ष रोबोट",
    tagline_kannada: "ಭವಿಷ್ಯದ ಧೈರ್ಯಶಾಲಿ ಬಾಹ್ಯಾಕಾಶ ರೋಬೋಟ್",
    type: "robotic",
    color: "#00D4FF",
    bgColor: "#001A2E",
    accentColor: "#00D4FF22",
    image: boltImg,
  },
  ZARA: {
    id: "ZARA",
    name: "ZARA",
    tagline: "Cheerful alien from planet Zorb",
    tagline_hindi: "ज़ोर्ब ग्रह की खुशमिज़ाज एलियन",
    tagline_kannada: "ಝೋರ್ಬ್ ಗ್ರಹದ ಸಂತೋಷದ ಏಲಿಯನ್",
    type: "cartoonish",
    color: "#FF6BFF",
    bgColor: "#1A0A2E",
    accentColor: "#FF6BFF22",
    image: zaraImg,
  },
  NOVA: {
    id: "NOVA",
    name: "NOVA",
    tagline: "Calm and wise space AI",
    tagline_hindi: "शांत और बुद्धिमान अंतरिक्ष AI",
    tagline_kannada: "ಶಾಂತ ಮತ್ತು ಜ್ಞಾನಿ ಬಾಹ್ಯಾಕಾಶ AI",
    type: "semi-robotic",
    color: "#A8FF6F",
    bgColor: "#0A1A08",
    accentColor: "#A8FF6F22",
    image: novaImg,
  },
  BEEP: {
    id: "BEEP",
    name: "BEEP",
    tagline: "Tiny helper robot who loves learning",
    tagline_hindi: "सीखने का शौकीन छोटा सहायक रोबोट",
    tagline_kannada: "ಕಲಿಯಲು ಇಷ್ಟಪಡುವ ಪುಟ್ಟ ಸಹಾಯಕ ರೋಬೋಟ್",
    type: "cartoonish",
    color: "#FFD166",
    bgColor: "#1A1400",
    accentColor: "#FFD16622",
    image: beepImg,
  },
  ECHO: {
    id: "ECHO",
    name: "ECHO",
    tagline: "Ancient computer from a distant galaxy",
    tagline_hindi: "दूर की आकाशगंगा का प्राचीन कंप्यूटर",
    tagline_kannada: "ದೂರದ ನಕ್ಷತ್ರಪುಂಜದ ಪ್ರಾಚೀನ ಕಂಪ್ಯೂಟರ್",
    type: "robotic",
    color: "#FF6B35",
    bgColor: "#1A0A00",
    accentColor: "#FF6B3522",
    image: echoImg,
  },
  MIRA: {
    id: "MIRA",
    name: "MIRA",
    tagline: "Friendly underwater robot",
    type: "cartoonish",
    color: "#06D6D6",
    bgColor: "#001A1A",
    accentColor: "#06D6D622",
    image: miraImg,
  },
};
