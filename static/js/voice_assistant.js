/**
 * RationSmart - Rural Accessibility & Voice Assistance Engine
 * Uses W3C Web Speech API (speechSynthesis)
 * 100% Offline-capable, zero external API keys.
 * 
 * 100% PURE TAMIL & PHONETIC TAMIL CONVERSION:
 * Converts all numbers (15, 20, 6, 1) and units (kg, liter) into pure Tamil words:
 * e.g. "அரிசி இருபது கிலோ" / "Arisi Irupathu kilo" (Never "arisi 20kg"!)
 */

class PDSVoiceAssistant {
    constructor() {
        this.synth = ('speechSynthesis' in window) ? window.speechSynthesis : null;
        this.isSpeaking = false;
        this.currentButton = null;
        this.lang = localStorage.getItem('pds_voice_lang') || 'ta'; // 'ta' for Tamil, 'en' for English
        this.voices = [];

        if (this.synth) {
            this.initVoices();
            if (this.synth.onvoiceschanged !== undefined) {
                this.synth.onvoiceschanged = () => this.initVoices();
            }
        }
    }

    initVoices() {
        if (!this.synth) return;
        this.voices = this.synth.getVoices() || [];
    }

    findTamilVoice() {
        if (!this.voices || this.voices.length === 0) {
            this.initVoices();
        }
        return this.voices.find(v => 
            v.lang.toLowerCase() === 'ta-in' || 
            v.lang.toLowerCase() === 'ta_in' || 
            v.lang.toLowerCase().startsWith('ta') ||
            v.name.toLowerCase().includes('tamil') ||
            v.name.toLowerCase().includes('valluvar') ||
            v.name.toLowerCase().includes('pallavi')
        ) || null;
    }

    findIndianEnglishVoice() {
        if (!this.voices || this.voices.length === 0) {
            this.initVoices();
        }
        return this.voices.find(v => 
            v.lang.toLowerCase() === 'en-in' || 
            v.lang.toLowerCase() === 'en_in' ||
            v.name.toLowerCase().includes('india') ||
            v.name.toLowerCase().includes('heera') ||
            v.name.toLowerCase().includes('ravi')
        ) || this.voices.find(v => v.lang.startsWith('en')) || null;
    }

    setLanguage(newLang) {
        this.lang = newLang === 'en' ? 'en' : 'ta';
        localStorage.setItem('pds_voice_lang', this.lang);
    }

    stop() {
        if (this.synth) {
            this.synth.cancel();
        }
        this.resetButton();
        this.isSpeaking = false;
    }

    resetButton() {
        if (this.currentButton) {
            const originalHtml = this.currentButton.getAttribute('data-original-html');
            if (originalHtml) {
                this.currentButton.innerHTML = originalHtml;
            }
            this.currentButton.classList.remove('btn-danger');
            this.currentButton = null;
        }
    }

    speakPayload({ textTamil, textTanglish, textEnglish, triggerButton = null }) {
        if (!this.synth) {
            alert('Your device or browser does not support Voice Speech Synthesis.');
            return;
        }

        // If currently speaking, stop it
        if (this.isSpeaking) {
            this.stop();
            if (triggerButton && triggerButton === this.currentButton) {
                return; // User clicked stop
            }
        }

        // Always refresh voices before playing
        this.initVoices();

        const tamilVoice = this.findTamilVoice();
        const indianVoice = this.findIndianEnglishVoice();

        let textToSpeak = '';
        let utteranceLang = 'ta-IN';
        let selectedVoice = null;

        if (this.lang === 'en') {
            // User explicitly requested English
            textToSpeak = textEnglish;
            utteranceLang = 'en-IN';
            selectedVoice = indianVoice;
        } else {
            // User wants Tamil (DEFAULT)
            if (tamilVoice) {
                // Native Tamil voice is installed (e.g. Edge Natural Valluvar/Pallavi or Chrome Tamil)
                textToSpeak = textTamil;
                utteranceLang = 'ta-IN';
                selectedVoice = tamilVoice;
            } else {
                // No native Tamil voice installed on OS -> Speak 100% Phonetic Tamil (Tanglish)
                // Using Indian English voice so it speaks genuine Tamil words!
                textToSpeak = textTanglish;
                utteranceLang = 'en-IN';
                selectedVoice = indianVoice;
            }
        }

        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.lang = utteranceLang;
        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }
        utterance.rate = 0.88; // Calm and clear pace
        utterance.pitch = 1.0;

        if (triggerButton) {
            this.currentButton = triggerButton;
            if (!triggerButton.getAttribute('data-original-html')) {
                triggerButton.setAttribute('data-original-html', triggerButton.innerHTML);
            }
            triggerButton.innerHTML = '<i class="bi bi-stop-circle-fill me-1 text-danger"></i> நிறுத்து (Stop)';
        }

        this.isSpeaking = true;

        utterance.onend = () => {
            this.isSpeaking = false;
            this.resetButton();
        };

        utterance.onerror = (e) => {
            console.warn('[Voice Assistant] Playback error or cancelled:', e);
            this.isSpeaking = false;
            this.resetButton();
        };

        this.synth.speak(utterance);
    }

    // High-Level Helper: Speak Beneficiary Quota
    speakBeneficiaryQuota(cardHolder, cardType, quotaItems, triggerButton = null) {
        const cardTypeTamil = translateCardTypeToTamil(cardType);
        const cardTypeTanglish = translateCardTypeToTanglish(cardType);

        // 1. Pure Tamil Text (Numbers converted to Tamil words: "பதினைந்து கிலோ", "இருபது கிலோ")
        const tamilItems = quotaItems.map(item => {
            const comm = translateCommodityToTamil(item.name || item.commodity_name);
            const unit = translateUnitToTamil(item.unit);
            const qtyRaw = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            const qtyWords = numberToTamilWords(qtyRaw);
            return `${comm} ${qtyWords} ${unit}`;
        }).join(', ');

        const textTamil = `வணக்கம் ${cardHolder} அவர்களே! உங்கள் ${cardTypeTamil}க்கான இந்த மாத உணவுப் பொருள் ஒதுக்கீடு விவரம்: ${tamilItems}. நியாய விலைக் கடையில் பெற்றுக்கொள்ளலாம். நன்றி!`;

        // 2. Tanglish Phonetic Text (Phonetic Tamil words: "Arisi irupathu kilo, Gothumai aaru kilo")
        const tanglishItems = quotaItems.map(item => {
            const comm = translateCommodityToTanglish(item.name || item.commodity_name);
            const unit = translateUnitToTanglish(item.unit);
            const qtyRaw = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            const qtyWords = numberToTanglishWords(qtyRaw);
            return `${comm} ${qtyWords} ${unit}`;
        }).join(', ');

        const textTanglish = `Vanakkam ${cardHolder} avargaley! Ungal ${cardTypeTanglish}-kkaana intha maatha unavu porul othukkeedu vivaram: ${tanglishItems}. Niyaya vilai kadaiyil petruk kollalaam. Nandri!`;

        // 3. English Text
        const englishItems = quotaItems.map(item => {
            const qty = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            return `${qty} ${item.unit} of ${item.name || item.commodity_name}`;
        }).join(', ');

        const textEnglish = `Hello ${cardHolder}. Your monthly quota for ${cardType} ration card is: ${englishItems}. Thank you.`;

        this.speakPayload({
            textTamil,
            textTanglish,
            textEnglish,
            triggerButton
        });
    }

    // High-Level Helper: Speak Sale / Bill Receipt
    speakSaleReceipt(billNumber, cardHolder, items, totalAmount, triggerButton = null) {
        const amtVal = parseFloat(totalAmount) || 0;
        const cleanBill = billNumber ? String(billNumber).replace(/-/g, ' ') : '';

        // 1. Pure Tamil Text
        const tamilItems = items.map(item => {
            const comm = translateCommodityToTamil(item.name || item.commodity_name);
            const unit = translateUnitToTamil(item.unit);
            const qtyWords = numberToTamilWords(item.quantity);
            return `${comm} ${qtyWords} ${unit}`;
        }).join(', ');

        const amtTamil = amtVal === 0 ? 'முற்றிலும் இலவசம்' : `${numberToTamilWords(amtVal)} ரூபாய்`;
        const textTamil = `வணக்கம் ${cardHolder} அவர்களே! பில் எண் ${cleanBill}. வழங்கப்பட்ட உணவுப் பொருட்கள்: ${tamilItems}. மொத்த தொகை: ${amtTamil}. பொருட்கள் வெற்றிகரமாக வழங்கப்பட்டது. நன்றி!`;

        // 2. Tanglish Phonetic Text
        const tanglishItems = items.map(item => {
            const comm = translateCommodityToTanglish(item.name || item.commodity_name);
            const unit = translateUnitToTanglish(item.unit);
            const qtyWords = numberToTanglishWords(item.quantity);
            return `${comm} ${qtyWords} ${unit}`;
        }).join(', ');

        const amtTanglish = amtVal === 0 ? 'Muttrilum Ilavasam' : `${numberToTanglishWords(amtVal)} Roobai`;
        const textTanglish = `Vanakkam ${cardHolder} avargaley! Bill en ${cleanBill}. Vazhangappatta unavu porutkal: ${tanglishItems}. Mottha thogai: ${amtTanglish}. Porutkal vetrigaramaaga vazhangappattathu. Nandri!`;

        // 3. English Text
        const englishItems = items.map(item => `${item.quantity} ${item.unit} of ${item.name || item.commodity_name}`).join(', ');
        const amtEnglish = amtVal === 0 ? 'Zero Rupees (Free Scheme)' : `${amtVal.toFixed(2)} Rupees`;
        const textEnglish = `Hello ${cardHolder}. Bill number ${billNumber}. Disbursed items: ${englishItems}. Total bill amount: ${amtEnglish}. Transaction completed successfully. Thank you.`;

        this.speakPayload({
            textTamil,
            textTanglish,
            textEnglish,
            triggerButton
        });
    }
}

// =========================================================================
// Number to Tamil & Tanglish Words Converters (No raw numbers!)
// =========================================================================

function numberToTamilWords(n) {
    n = parseFloat(n) || 0;
    if (n === 0) return 'பூஜ்ஜியம்';
    if (Math.abs(n - 0.5) < 0.05) return 'அரை';

    const ones = ['', 'ஒன்று', 'இரண்டு', 'மூன்று', 'நான்கு', 'ஐந்து', 'ஆறு', 'ஏழு', 'எட்டு', 'ஒன்பது'];
    const teens = {
        10: 'பத்து', 11: 'பதினொன்று', 12: 'பன்னிரண்டு', 13: 'பதின்மூன்று', 14: 'பதினான்கு',
        15: 'பதினைந்து', 16: 'பதினாறு', 17: 'பதினேழு', 18: 'பதினெட்டு', 19: 'பத்தொன்பது'
    };
    const tens = ['', '', 'இருபது', 'முப்பது', 'நாற்பது', 'ஐம்பது', 'அறுபது', 'எழுபது', 'எண்பது', 'தொண்ணூறு'];
    const tensPrefix = ['', '', 'இருபத்து ', 'முப்பத்து ', 'நாற்பத்து ', 'ஐம்பத்து ', 'அறுபத்து ', 'எழுபத்து ', 'எண்பத்து ', 'தொண்ணூற்று '];

    const intPart = Math.floor(n);
    const hasHalf = (n % 1 >= 0.4 && n % 1 <= 0.6);

    let word = '';
    if (intPart < 10) {
        word = (intPart === 1) ? 'ஒரு' : ones[intPart];
    } else if (intPart >= 10 && intPart < 20) {
        word = teens[intPart];
    } else if (intPart >= 20 && intPart < 100) {
        const t = Math.floor(intPart / 10);
        const rem = intPart % 10;
        if (rem === 0) {
            word = tens[t];
        } else {
            word = tensPrefix[t] + (rem === 1 ? 'ஒரு' : ones[rem]);
        }
    } else {
        word = String(intPart);
    }

    if (hasHalf) {
        if (intPart === 0) return 'அரை';
        if (intPart === 1) return 'ஒன்றரை';
        if (intPart === 2) return 'இரண்டரை';
        return word + ' அரை';
    }

    return word;
}

function numberToTanglishWords(n) {
    n = parseFloat(n) || 0;
    if (n === 0) return 'Poojiyam';
    if (Math.abs(n - 0.5) < 0.05) return 'Arai';

    const ones = ['', 'Ondru', 'Irandu', 'Moondru', 'Naangu', 'Ainthu', 'Aaru', 'Yezhu', 'Yettu', 'Onpathu'];
    const teens = {
        10: 'Pathu', 11: 'Pathinondru', 12: 'Pannirandu', 13: 'Pathinmoondru', 14: 'Pathinaangu',
        15: 'Pathinainthu', 16: 'Pathinaaru', 17: 'Pathinezhu', 18: 'Pathinettu', 19: 'Pathonpathu'
    };
    const tens = ['', '', 'Irupathu', 'Muppathu', 'Naarpathu', 'Aimpathu', 'Arupathu', 'Yezhupathu', 'Yenpathu', 'Thonnooru'];
    const tensPrefix = ['', '', 'Irupaththe ', 'Muppaththe ', 'Naarpaththe ', 'Aimpaththe ', 'Arupaththe ', 'Yezhupaththe ', 'Yenpaththe ', 'Thonnootru '];

    const intPart = Math.floor(n);
    const hasHalf = (n % 1 >= 0.4 && n % 1 <= 0.6);

    let word = '';
    if (intPart < 10) {
        word = (intPart === 1) ? 'Oru' : ones[intPart];
    } else if (intPart >= 10 && intPart < 20) {
        word = teens[intPart];
    } else if (intPart >= 20 && intPart < 100) {
        const t = Math.floor(intPart / 10);
        const rem = intPart % 10;
        if (rem === 0) {
            word = tens[t];
        } else {
            word = tensPrefix[t] + (rem === 1 ? 'Oru' : ones[rem]);
        }
    } else {
        word = String(intPart);
    }

    if (hasHalf) {
        if (intPart === 0) return 'Arai';
        if (intPart === 1) return 'Ondrarai';
        if (intPart === 2) return 'Irandarai';
        return word + ' arai';
    }

    return word;
}

// =========================================================================
// Card Type Translation Helpers
// =========================================================================

function translateCardTypeToTamil(cardType) {
    if (!cardType) return 'ரேஷன் அட்டை';
    const ct = cardType.toUpperCase();
    if (ct.includes('AAY')) return 'அந்தியோதயா அன்ன யோஜனா மஞ்சள் அட்டை';
    if (ct.includes('PHH')) return 'முன்னுரிமை குடும்ப அட்டை';
    if (ct.includes('NPHH')) return 'முன்னுரிமையற்ற குடும்ப அட்டை';
    if (ct.includes('AY')) return 'அன்னபூர்ணா முதியோர் அட்டை';
    return `${cardType} அட்டை`;
}

function translateCardTypeToTanglish(cardType) {
    if (!cardType) return 'ration card';
    const ct = cardType.toUpperCase();
    if (ct.includes('AAY')) return 'Anthiyodhaya Anna Yojana card';
    if (ct.includes('PHH')) return 'Munnurimai Kudumba card';
    if (ct.includes('NPHH')) return 'Munnurimaiyatra Kudumba card';
    if (ct.includes('AY')) return 'Annapoorna Muthiyor card';
    return `${cardType} card`;
}

// =========================================================================
// Commodity & Unit Translation Helpers
// =========================================================================

function translateCommodityToTamil(name) {
    if (!name) return 'பொருள்';
    const n = name.toLowerCase();
    if (n.includes('rice')) return 'அரிசி';
    if (n.includes('wheat') || n.includes('atta')) return 'கோதுமை';
    if (n.includes('sugar')) return 'சர்க்கரை';
    if (n.includes('kerosene')) return 'மண்ணெண்ணெய்';
    if (n.includes('dal') || n.includes('pulse')) return 'துவரம் பருப்பு';
    if (n.includes('oil')) return 'பாமாயில்';
    return name;
}

function translateUnitToTamil(unit) {
    if (!unit) return '';
    const u = unit.toLowerCase();
    if (u.includes('kg')) return 'கிலோ';
    if (u.includes('liter') || u.includes('litre')) return 'லிட்டர்';
    return unit;
}

function translateCommodityToTanglish(name) {
    if (!name) return 'porul';
    const n = name.toLowerCase();
    if (n.includes('rice')) return 'Arisi';
    if (n.includes('wheat') || n.includes('atta')) return 'Gothumai';
    if (n.includes('sugar')) return 'Sarkkarai';
    if (n.includes('kerosene')) return 'Mannenney';
    if (n.includes('dal') || n.includes('pulse')) return 'Thuvaram Paruppu';
    if (n.includes('oil')) return 'Paamayil';
    return name;
}

function translateUnitToTanglish(unit) {
    if (!unit) return '';
    const u = unit.toLowerCase();
    if (u.includes('kg')) return 'kilo';
    if (u.includes('liter') || u.includes('litre')) return 'liter';
    return unit;
}

// Global Singleton Instance
window.pdsVoice = new PDSVoiceAssistant();
