/* ===================================
   AgroVision - Localization Module
   =================================== */

const AgroVisionLanguage = (function() {
    'use strict';

    // 1. FULL DICTIONARY
    const translations = {
        en: {
            // --- Navigation ---
            appName: "AgroVision",
            navHome: "Home",
            navDetect: "Detect Disease",
            navSchemes: "Govt Schemes",
            navVoice: "Voice Help",

            // --- Hero Section ---
            heroTitle: "🌾 Welcome to AgroVision",
            heroSubtitle: "AI Powered Plant & Seed Disease Detection",
            heroDescription: "Empowering farmers with cutting-edge AI technology to detect plant diseases early, improve crop health, and increase productivity.",
            btnGetStarted: "Get Started",
            btnLearnMore: "Learn More",
            
            // --- Common UI ---
            loading: "Processing...",
            success: "Success",
            error: "Error",

            // --- Detection Page ---
            detectTitle: "🔍 Disease Detection",
            detectSubtitle: "Upload an image to detect plant diseases or seed defects",
            uploadLabel: "Select Image:",
            uploadText: "Click or drag to upload image",
            uploadHint: "Supported: PNG, JPG, JPEG (Max 5MB)",
            categoryLabel: "Select Category:",
            leafOption: "Leaf Disease",
            leafOptionDesc: "Detect diseases on plant leaves",
            seedOption: "Seed Defect",
            seedOptionDesc: "Analyze seed quality issues",
            btnAnalyze: "Analyze Image",

            // --- Results Page ---
            resultTitle: "🔬 Detection Results",
            uploadedImage: "Uploaded Image",
            confidence: "Confidence",
            treatmentTitle: "💊 Recommended Treatment",
            preventionTitle: "🛡️ Prevention Tips",
            btnAnalyzeAnother: "Analyze Another Image",
            btnViewSchemes: "View Govt Schemes",
            importantNote: "📌 Important Note",
            noteText: "This AI analysis is for guidance purposes. For severe infections, please consult with local agricultural experts.",

            // --- Schemes Page ---
            schemesTitle: "🏛️ Government Agricultural Schemes",
            schemesSubtitle: "Access information about subsidies, loans, and support programs",
            selectCrop: "Select Crop Type:",
            selectState: "Select State:",
            allStates: "All States",
            allCrops: "All Crops",
            eligibility: "Eligibility:",
            benefit: "Benefit:",
            learnMoreLink: "Learn More →",
            searchPlaceholder: "Search schemes...",
            
            // Scheme Cards
            centralGovt: "Central Govt",
            stateGovtTelangana: "Telangana",
            stateGovtAndhra: "Andhra Pradesh",
            
            scheme1Title: "PM-KISAN Samman Nidhi",
            scheme1Desc: "Financial benefit of ₹6,000/- per year in three equal installments to all landholding farmer families.",
            scheme1Benefit: "Benefit: ₹6,000/year",
            
            scheme2Title: "Pradhan Mantri Fasal Bima",
            scheme2Desc: "Comprehensive crop insurance providing coverage against non-preventable natural risks from pre-sowing to post-harvest.",
            scheme2Benefit: "Coverage: Crop Loss",
            
            scheme3Title: "Rythu Bandhu Scheme",
            scheme3Desc: "Investment support scheme for agriculture and horticulture crops by way of grant to purchase inputs.",
            scheme3Benefit: "Benefit: ₹10,000/acre",
            
            scheme4Title: "YSR Rythu Bharosa",
            scheme4Desc: "Financial assistance to farmer families including tenant farmers to support their investment needs.",
            scheme4Benefit: "Benefit: ₹13,500/year",
            
            scheme5Title: "Soil Health Card Scheme",
            scheme5Desc: "Get a report card on the nutrient status of your holding and advice on dosage of fertilizers.",
            scheme5Benefit: "Free Soil Testing",
            
            scheme6Title: "Kisan Credit Card (KCC)",
            scheme6Desc: "Timely access to credit for farmers to meet their cultivation and other needs.",
            scheme6Benefit: "Low Interest Loan",
            
            btnCheckEligibility: "Check Eligibility",
            btnApply: "Apply",
            btnDetails: "Details",
            btnLocateLab: "Locate Lab",
            btnRegister: "Register",

            // --- Voice/Helpline ---
            tollFreeTitle: "Toll-Free Helpline",
            helplineAvailability: "Available 24/7 • Multi-lingual Support",
            tapToCall: "Tap to Call Now",
            ivrExperience: "Experience the IVR System",
            ivrDescription: "Not sure how it works? Try our interactive simulator. Our smart voice bot guides you through the process step-by-step in your local language.",
            playDemo: "▶️ Play Demo",
            welcomeMsg: "Hello! Welcome to AgroVision helpline.",
            tapPlayDemo: "Tap 'Play Demo'",
            
            ivrStep4Title: "Get Solution",
            ivrStep4Desc: "Our AI identifies the problem and dictates the remedy instantly.",
            ivrStep5Title: "SMS Confirmation",
            ivrStep5Desc: "You will receive an SMS with the medicine name and dosage instructions.",
            
            servicesOffered: "Services Offered",
            serviceDiseaseTitle: "Disease Diagnosis",
            serviceDiseaseDesc: "Identify crop diseases by describing symptoms.",
            serviceSchemeTitle: "Scheme Info",
            serviceSchemeDesc: "Get details on latest government subsidies.",
            serviceWeatherTitle: "Weather Alert",
            serviceWeatherDesc: "Get 3-day forecast warnings for your area.",
            supportedLanguages: "Supported Languages",

            // --- Homepage ---
            aiBadge: "✨ AI-Powered Farming",
            welcomeTo: "Welcome to",
            heroDescription: "Identify plant diseases instantly, access government schemes, and get expert advice—all in one place.",
            btnStartDetection: "🚀 Start Detection",
            liveAnalysis: "Live Analysis",
            statusActive: "● Active",
            confidenceLabel: "Confidence",
            humidityLabel: "Humidity",
            windLabel: "Wind",
            conditionLabel: "Condition",
            conditionGood: "Good",
            
            ourFeatures: "Our Features",
            featuresSubtitle: "Everything you need for a healthy harvest",
            featureDiseaseTitle: "Disease Detection",
            featureDiseaseDesc: "Upload photos of leaves or seeds to get instant diagnosis and remedies.",
            featureTryNow: "Try Now →",
            featureSchemeTitle: "Government Schemes",
            featureSchemeDesc: "Stay updated with the latest subsidies, loans, and agricultural policies.",
            featureViewSchemes: "View Schemes →",
            featureVoiceTitle: "Voice Assistant",
            featureVoiceDesc: "Can't type? Speak to our AI assistant in your local language.",
            featureGetHelp: "Get Help →",
            
            howItWorks: "How It Works",
            step1Title: "Upload Photo",
            step1Desc: "Take a clear picture of the affected plant part.",
            step2Title: "AI Analysis",
            step2Desc: "Our model identifies the disease in seconds.",
            step3Title: "Get Remedy",
            step3Desc: "Receive treatment steps and preventive advice.",
            
            footerTagline: "Empowering farmers with technology for a better tomorrow.",
            footerQuickLinks: "Quick Links",
            footerContact: "Contact",
            copyright: "©",
            allRightsReserved: "All rights reserved.",
            mobileDetect: "Detect",
            mobileSchemes: "Schemes",
            mobileHelp: "Help",

            // --- Voice Page ---
            voiceTitle: "🎤 Voice Assistance (IVR)",
            voiceSubtitle: "Help for farmers without smartphone access",
            callNow: "Call Our Toll-Free Helpline",
            availableHours: "Available 24/7 in regional languages",
            howIvrWorks: "How It Works",
            ivrStep1Title: "Call Helpline",
            ivrStep1Desc: "Dial 1800-123-4567",
            ivrStep2Title: "Select Language",
            ivrStep2Desc: "Choose your preferred language",
            ivrStep3Title: "Describe Issue",
            ivrStep3Desc: "Speak clearly about the symptoms",
            readyToCall: "Ready to Get Help?",
            
            // --- Footer ---
            footerAbout: "About AgroVision",
            footerAboutText: "AI-powered platform helping farmers detect plant diseases and improve crop health.",
            footerQuickLinks: "Quick Links",
            footerContact: "Contact",
            footerCopyright: "© 2026 AgroVision. All rights reserved."
        },

        te: {
            // --- Navigation ---
            appName: "అగ్రోవిజన్",
            navHome: "హోమ్",
            navDetect: "వ్యాధి గుర్తింపు",
            navSchemes: "పథకాలు",
            navVoice: "వాయిస్ సహాయం",

            // --- Hero ---
            heroTitle: "🌾 అగ్రోవిజన్‌కు స్వాగతం",
            heroSubtitle: "AI ఆధారిత మొక్క & విత్తన వ్యాధి గుర్తింపు",
            heroDescription: "మొక్కల వ్యాధులను ముందుగా గుర్తించి, పంట ఆరోగ్యాన్ని మెరుగుపరచడానికి అత్యాధునిక సాంకేతికత.",
            btnGetStarted: "ప్రారంభించండి",
            btnLearnMore: "మరింత తెలుసుకోండి",

            // --- Detection ---
            detectTitle: "🔍 వ్యాధి గుర్తింపు",
            detectSubtitle: "వ్యాధులను గుర్తించడానికి ఫోటో అప్‌లోడ్ చేయండి",
            uploadLabel: "చిత్రాన్ని ఎంచుకోండి:",
            uploadText: "ఇక్కడ క్లిక్ చేయండి",
            uploadHint: "మద్దతు: PNG, JPG (గరిష్టం 5MB)",
            categoryLabel: "వర్గం:",
            leafOption: "ఆకు వ్యాధి",
            leafOptionDesc: "ఆకులపై వ్యాధులను గుర్తించండి",
            seedOption: "విత్తన లోపం",
            seedOptionDesc: "విత్తన నాణ్యతను పరీక్షించండి",
            btnAnalyze: "విశ్లేషించండి",

            // --- Results ---
            resultTitle: "🔬 ఫలితాలు",
            uploadedImage: "అప్‌లోడ్ చేసిన చిత్రం",
            confidence: "నమ్మకం",
            treatmentTitle: "💊 చికిత్స",
            preventionTitle: "🛡️ నివారణ చర్యలు",
            btnAnalyzeAnother: "మరొకటి విశ్లేషించండి",
            btnViewSchemes: "పథకాలను చూడండి",
            importantNote: "📌 గమనిక",
            noteText: "ఇది AI విశ్లేషణ మాత్రమే. తీవ్రమైన సమస్యలకు వ్యవసాయ అధికారిని సంప్రదించండి.",

            // --- Schemes ---
            schemesTitle: "🏛️ ప్రభుత్వ పథకాలు",
            schemesSubtitle: "సబ్సిడీలు మరియు రుణాల సమాచారం",
            selectCrop: "పంట రకం:",
            selectState: "రాష్ట్రం:",
            allStates: "అన్ని రాష్ట్రాలు",
            allCrops: "అన్ని పంటలు",
            eligibility: "అర్హత:",
            benefit: "ప్రయోజనం:",
            learnMoreLink: "వివరాలు →",
            searchPlaceholder: "పథకాలను వెతకండి...",
            
            // Scheme Cards
            centralGovt: "కేంద్ర ప్రభుత్వం",
            stateGovtTelangana: "తెలంగాణ",
            stateGovtAndhra: "ఆంధ్ర ప్రదేశ్",
            
            scheme1Title: "PM-KISAN సమ్మాన్ నిధి",
            scheme1Desc: "భూస్వామ్య రైతు కుటుంబాలకు సంవత్సరానికి ₹6,000/- మూడు సమాన వాయిదాలలో ఆర్థిక ప్రయోజనం.",
            scheme1Benefit: "ప్రయోజనం: ₹6,000/సంవత్సరం",
            
            scheme2Title: "ప్రధాన మంత్రి ఫసల్ బీమా",
            scheme2Desc: "విత్తనం ముందు నుండి కోత తర్వాత వరకు నివారించలేని సహజ ప్రమాదాలకు వ్యతిరేకంగా సమగ్ర పంట బీమా.",
            scheme2Benefit: "కవరేజీ: పంట నష్టం",
            
            scheme3Title: "రైతు బంధు పథకం",
            scheme3Desc: "ఇన్‌పుట్‌లను కొనుగోలు చేయడానికి మంజూరు ద్వారా వ్యవసాయం మరియు ఉద్యాన పంటలకు పెట్టుబడి మద్దతు పథకం.",
            scheme3Benefit: "ప్రయోజనం: ₹10,000/ఎకరానికి",
            
            scheme4Title: "YSR రైతు భరోసా",
            scheme4Desc: "రైతు కుటుంబాలకు మరియు కౌలు రైతులకు వారి పెట్టుబడి అవసరాలను సమర్థించడానికి ఆర్థిక సహాయం.",
            scheme4Benefit: "ప్రయోజనం: ₹13,500/సంవత్సరం",
            
            scheme5Title: "నేల ఆరోగ్య కార్డ్ పథకం",
            scheme5Desc: "మీ భూమి పోషక స్థితిపై నివేదిక కార్డు మరియు ఎరువుల మోతాదుపై సలహా పొందండి.",
            scheme5Benefit: "ఉచిత నేల పరీక్ష",
            
            scheme6Title: "కిసాన్ క్రెడిట్ కార్డ్ (KCC)",
            scheme6Desc: "రైతులు వారి సాగు మరియు ఇతర అవసరాలను తీర్చడానికి సకాలంలో రుణాలకు యాక్సెస్.",
            scheme6Benefit: "తక్కువ వడ్డీ రుణం",
            
            btnCheckEligibility: "అర్హతను తనిఖీ చేయండి",
            btnApply: "దరఖాస్తు చేయండి",
            btnDetails: "వివరాలు",
            btnLocateLab: "ప్రయోగశాలను గుర్తించండి",
            btnRegister: "నమోదు చేయండి",

            // --- Voice/Helpline ---
            tollFreeTitle: "టోల్-ఫ్రీ హెల్ప్‌లైన్",
            helplineAvailability: "24/7 అందుబాటులో • బహుళ భాషా మద్దతు",
            tapToCall: "ఇప్పుడే కాల్ చేయండి",
            ivrExperience: "IVR సిస్టమ్‌ను అనుభవించండి",
            ivrDescription: "ఇది ఎలా పని చేస్తుందో ఖచ్చితంగా తెలియదా? మా ఇంటరాక్టివ్ సిమ్యులేటర్‌ను ప్రయత్నించండి. మా స్మార్ట్ వాయిస్ బాట్ మీ స్థానిక భాషలో దశల వారీగా మీకు మార్గనిర్దేశం చేస్తుంది.",
            playDemo: "▶️ డెమో ప్లే చేయండి",
            welcomeMsg: "నమస్కారం! ఎగ్రోవిజన్ హెల్ప్‌లైన్‌కు స్వాగతం.",
            tapPlayDemo: "'డెమో ప్లే చేయండి' నొక్కండి",
            
            ivrStep4Title: "పరిష్కారం పొందండి",
            ivrStep4Desc: "మా AI సమస్యను గుర్తిస్తుంది మరియు వెంటనే పరిష్కారాన్ని నిర్దేశిస్తుంది.",
            ivrStep5Title: "SMS నిర్ధారణ",
            ivrStep5Desc: "మందు పేరు మరియు మోతాదు సూచనలతో మీకు SMS వస్తుంది.",
            
            servicesOffered: "అందించే సేవలు",
            serviceDiseaseTitle: "వ్యాధి నిర్ధారణ",
            serviceDiseaseDesc: "లక్షణాలను వివరించడం ద్వారా పంట వ్యాధులను గుర్తించండి.",
            serviceSchemeTitle: "పథకాల సమాచారం",
            serviceSchemeDesc: "తాజా ప్రభుత్వ రాయితీలపై వివరాలు పొందండి.",
            serviceWeatherTitle: "వాతావరణ హెచ్చరిక",
            serviceWeatherDesc: "మీ ప్రాంతానికి 3 రోజుల సూచన హెచ్చరికలు పొందండి.",
            supportedLanguages: "మద్దతు ఉన్న భాషలు",

            // --- Homepage ---
            aiBadge: "✨ AI-ఆధారిత వ్యవసాయం",
            welcomeTo: "స్వాగతం",
            heroDescription: "మొక్కల వ్యాధులను తక్షణమే గుర్తించండి, ప్రభుత్వ పథకాలను యాక్సెస్ చేయండి మరియు నిపుణుల సలహాను పొందండి—అన్నీ ఒకే చోట.",
            btnStartDetection: "🚀 గుర్తింపు ప్రారంభించండి",
            liveAnalysis: "లైవ్ విశ్లేషణ",
            statusActive: "● చురుకుగా",
            confidenceLabel: "విశ్వాసం",
            humidityLabel: "తేమ",
            windLabel: "గాలి",
            conditionLabel: "పరిస్థితి",
            conditionGood: "మంచిది",
            
            ourFeatures: "మా లక్షణాలు",
            featuresSubtitle: "ఆరోగ్యకరమైన పంట కోసం మీకు అవసరమైన ప్రతిదీ",
            featureDiseaseTitle: "వ్యాధి గుర్తింపు",
            featureDiseaseDesc: "తక్షణ నిర్ధారణ మరియు పరిష్కారాలను పొందడానికి ఆకులు లేదా విత్తనాల ఫోటోలను అప్‌లోడ్ చేయండి.",
            featureTryNow: "ఇప్పుడు ప్రయత్నించండి →",
            featureSchemeTitle: "ప్రభుత్వ పథకాలు",
            featureSchemeDesc: "తాజా రాయితీలు, రుణాలు మరియు వ్యవసాయ విధానాలతో నవీకరించబడండి.",
            featureViewSchemes: "పథకాలను చూడండి →",
            featureVoiceTitle: "వాయిస్ అసిస్టెంట్",
            featureVoiceDesc: "టైప్ చేయలేరా? మీ స్థానిక భాషలో మా AI అసిస్టెంట్‌తో మాట్లాడండి.",
            featureGetHelp: "సహాయం పొందండి →",
            
            howItWorks: "ఇది ఎలా పనిచేస్తుంది",
            step1Title: "ఫోటో అప్‌లోడ్ చేయండి",
            step1Desc: "ప్రభావితమైన మొక్క భాగం యొక్క స్పష్టమైన చిత్రాన్ని తీయండి.",
            step2Title: "AI విశ్లేషణ",
            step2Desc: "మా మోడల్ సెకన్లలో వ్యాధిని గుర్తిస్తుంది.",
            step3Title: "పరిష్కారం పొందండి",
            step3Desc: "చికిత్స దశలు మరియు నివారణ సలహాను స్వీకరించండి.",
            
            footerTagline: "రేపటి కోసం సాంకేతికతతో రైతులకు శక్తినివ్వడం.",
            footerQuickLinks: "శీఘ్ర లింక్‌లు",
            footerContact: "సంప్రదించండి",
            copyright: "©",
            allRightsReserved: "అన్ని హక్కులు రిజర్వ్ చేయబడ్డాయి.",
            mobileDetect: "గుర్తించు",
            mobileSchemes: "పథకాలు",
            mobileHelp: "సహాయం",

            btnRegister: "నమోదు చేయండి",

            // --- Voice ---
            voiceTitle: "🎤 వాయిస్ సహాయం",
            voiceSubtitle: "స్మార్ట్‌ఫోన్ లేని రైతులకు మద్దతు",
            callNow: "టోల్-ఫ్రీ నంబర్‌కు కాల్ చేయండి",
            availableHours: "24/7 అందుబాటులో ఉంది",
            howIvrWorks: "ఇది ఎలా పని చేస్తుంది",
            ivrStep1Title: "కాల్ చేయండి",
            ivrStep1Desc: "1800-123-4567 డయల్ చేయండి",
            ivrStep2Title: "భాష ఎంపిక",
            ivrStep2Desc: "తెలుగు ఎంచుకోండి",
            ivrStep3Title: "సమస్య చెప్పండి",
            ivrStep3Desc: "లక్షణాలను స్పష్టంగా చెప్పండి",
            readyToCall: "సహాయం కావాలా?",

            // --- Footer ---
            footerAbout: "మా గురించి",
            footerAboutText: "రైతులకు సహాయపడే AI ప్లాట్‌ఫారమ్.",
            footerQuickLinks: "లింకులు",
            footerContact: "సంప్రదించండి",
            footerCopyright: "© 2026 అగ్రోవిజన్. సర్వహక్కులు కేటాయించబడ్డాయి."
        },

        hi: {
            // --- Navigation ---
            appName: "एग्रोविज़न",
            navHome: "होम",
            navDetect: "रोग पहचान",
            navSchemes: "योजनाएं",
            navVoice: "वॉइस सहायता",

            // --- Hero ---
            heroTitle: "🌾 एग्रोविज़न में स्वागत है",
            heroSubtitle: "AI संचालित रोग पहचान",
            heroDescription: "फसलों के रोगों का जल्दी पता लगाने और उत्पादकता बढ़ाने के लिए आधुनिक तकनीक।",
            btnGetStarted: "शुरू करें",
            btnLearnMore: "और जानें",

            // --- Detection ---
            detectTitle: "🔍 रोग पहचान",
            detectSubtitle: "रोग का पता लगाने के लिए फोटो अपलोड करें",
            uploadLabel: "तस्वीर चुनें:",
            uploadText: "यहाँ क्लिक करें",
            uploadHint: "समर्थित: PNG, JPG (अधिकतम 5MB)",
            categoryLabel: "श्रेणी:",
            leafOption: "पत्ती रोग",
            leafOptionDesc: "पत्तियों पर रोग पहचानें",
            seedOption: "बीज दोष",
            seedOptionDesc: "बीज गुणवत्ता जांचें",
            btnAnalyze: "विश्लेषण करें",

            // --- Results ---
            resultTitle: "🔬 परिणाम",

            // --- Schemes ---
            schemesTitle: "🏛️ सरकारी योजनाएं",
            schemesSubtitle: "किसानों के लिए योजनाएं और लाभ",
            searchPlaceholder: "योजना खोजें...",
            selectState: "राज्य चुनें",
            allStates: "सभी राज्य",

            scheme1Title: "PM-KISAN सम्मान निधि",
            scheme1Desc: "सभी भूमिधारक किसान परिवारों को तीन समान किस्तों में प्रति वर्ष ₹6,000/- का वित्तीय लाभ।",
            scheme1Benefit: "लाभ: ₹6,000/वर्ष",

            scheme2Title: "प्रधान मंत्री फसल बीमा योजना",
            scheme2Desc: "कम प्रीमियम पर प्राकृतिक आपदाओं से फसल हानि के लिए बीमा कवरेज।",
            scheme2Benefit: "लाभ: फसल हानि कवरेज",

            scheme3Title: "रायथु बंधु योजना",
            scheme3Desc: "तेलंगाना के किसानों को दो फसल सीजनों के लिए प्रति एकड़ ₹5,000 की वित्तीय सहायता।",
            scheme3Benefit: "लाभ: ₹10,000/एकड़/वर्ष",

            scheme4Title: "YSR रायथु भरोसा",
            scheme4Desc: "आंध्र प्रदेश के किसानों को निवेश सहायता के रूप में प्रति वर्ष ₹13,500 की वित्तीय सहायता।",
            scheme4Benefit: "लाभ: ₹13,500/वर्ष",

            scheme5Title: "मृदा स्वास्थ्य कार्ड योजना",
            scheme5Desc: "किसानों को मिट्टी की पोषक स्थिति और उर्वरक सिफारिशों का विश्लेषण करने में मदद करता है।",
            scheme5Benefit: "लाभ: निःशुल्क मिट्टी परीक्षण",

            scheme6Title: "किसान क्रेडिट कार्ड (KCC)",
            scheme6Desc: "किसानों को फसल उत्पादन के लिए 7% ब्याज दर पर ₹3 लाख तक का ऋण।",
            scheme6Benefit: "लाभ: ₹3 लाख तक का ऋण",

            btnCheckEligibility: "पात्रता जांचें",
            btnApply: "आवेदन करें",
            btnDetails: "विवरण",
            btnLocateLab: "प्रयोगशाला खोजें",
            btnRegister: "पंजीकरण करें",

            centralGovt: "केंद्र सरकार",
            stateGovtTelangana: "तेलंगाना सरकार",
            stateGovtAndhra: "आंध्र प्रदेश सरकार",

            // --- Voice/Helpline ---
            tollFreeTitle: "टोल-फ्री हेल्पलाइन",
            helplineAvailability: "24/7 उपलब्ध • बहुभाषी सहायता",
            tapToCall: "अभी कॉल करें",
            ivrExperience: "IVR सिस्टम का अनुभव करें",
            ivrDescription: "यह कैसे काम करता है, सुनिश्चित नहीं हैं? हमारे इंटरैक्टिव सिम्युलेटर को आज़माएं। हमारा स्मार्ट वॉइस बॉट आपकी स्थानीय भाषा में चरण-दर-चरण मार्गदर्शन करता है।",
            playDemo: "▶️ डेमो चलाएं",
            welcomeMsg: "नमस्ते! एग्रोविज़न हेल्पलाइन में आपका स्वागत है।",
            tapPlayDemo: "'डेमो चलाएं' दबाएं",
            
            ivrStep4Title: "समाधान प्राप्त करें",
            ivrStep4Desc: "हमारा AI समस्या की पहचान करता है और तुरंत उपाय बताता है।",
            ivrStep5Title: "SMS पुष्टि",
            ivrStep5Desc: "आपको दवा के नाम और खुराक निर्देशों के साथ SMS प्राप्त होगा।",
            
            servicesOffered: "प्रदान की जाने वाली सेवाएं",
            serviceDiseaseTitle: "रोग निदान",
            serviceDiseaseDesc: "लक्षणों का वर्णन करके फसल रोगों की पहचान करें।",
            serviceSchemeTitle: "योजना जानकारी",
            serviceSchemeDesc: "नवीनतम सरकारी सब्सिडी का विवरण प्राप्त करें।",
            serviceWeatherTitle: "मौसम चेतावनी",
            serviceWeatherDesc: "अपने क्षेत्र के लिए 3-दिन का पूर्वानुमान चेतावनी प्राप्त करें।",
            supportedLanguages: "समर्थित भाषाएं",

            // --- Homepage ---
            aiBadge: "✨ AI-संचालित खेती",
            welcomeTo: "स्वागत है",
            heroDescription: "पौधों की बीमारियों को तुरंत पहचानें, सरकारी योजनाओं तक पहुंचें, और विशेषज्ञ सलाह प्राप्त करें—सब एक ही जगह।",
            btnStartDetection: "🚀 पहचान शुरू करें",
            liveAnalysis: "लाइव विश्लेषण",
            statusActive: "● सक्रिय",
            confidenceLabel: "विश्वास",
            humidityLabel: "नमी",
            windLabel: "हवा",
            conditionLabel: "स्थिति",
            conditionGood: "अच्छी",
            
            ourFeatures: "हमारी विशेषताएं",
            featuresSubtitle: "स्वस्थ फसल के लिए आपको जो कुछ भी चाहिए",
            featureDiseaseTitle: "रोग पहचान",
            featureDiseaseDesc: "तुरंत निदान और उपचार प्राप्त करने के लिए पत्तियों या बीजों की तस्वीरें अपलोड करें।",
            featureTryNow: "अभी आज़माएं →",
            featureSchemeTitle: "सरकारी योजनाएं",
            featureSchemeDesc: "नवीनतम सब्सिडी, ऋण और कृषि नीतियों के साथ अपडेट रहें।",
            featureViewSchemes: "योजनाएं देखें →",
            featureVoiceTitle: "वॉइस सहायक",
            featureVoiceDesc: "टाइप नहीं कर सकते? अपनी स्थानीय भाषा में हमारे AI सहायक से बात करें।",
            featureGetHelp: "मदद पाएं →",
            
            howItWorks: "यह कैसे काम करता है",
            step1Title: "फोटो अपलोड करें",
            step1Desc: "प्रभावित पौधे के हिस्से की स्पष्ट तस्वीर लें।",
            step2Title: "AI विश्लेषण",
            step2Desc: "हमारा मॉडल सेकंड में बीमारी की पहचान करता है।",
            step3Title: "उपचार प्राप्त करें",
            step3Desc: "उपचार के चरण और रोकथाम सलाह प्राप्त करें।",
            
            footerTagline: "बेहतर कल के लिए प्रौद्योगिकी से किसानों को सशक्त बनाना।",
            footerQuickLinks: "त्वरित लिंक",
            footerContact: "संपर्क",
            copyright: "©",
            allRightsReserved: "सर्वाधिकार सुरक्षित।",
            mobileDetect: "पहचानें",
            mobileSchemes: "योजनाएं",
            mobileHelp: "मदद",
            
            uploadedImage: "अपलोड की गई तस्वीर",
            confidence: "आत्मविश्वास",
            treatmentTitle: "💊 उपचार",
            preventionTitle: "🛡️ रोकथाम",
            btnAnalyzeAnother: "दूसरा विश्लेषण करें",
            btnViewSchemes: "योजनाएं देखें",
            importantNote: "📌 नोट",
            noteText: "यह केवल AI सलाह है। गंभीर समस्याओं के लिए कृषि अधिकारी से संपर्क करें।",

            // --- Schemes ---
            schemesTitle: "🏛️ सरकारी योजनाएं",
            schemesSubtitle: "सब्सिडी और ऋण की जानकारी",
            selectCrop: "फसल चुनें:",
            selectState: "राज्य:",
            allStates: "सभी राज्य",
            allCrops: "सभी फसलें",
            eligibility: "पात्रता:",
            benefit: "लाभ:",
            learnMoreLink: "विवरण →",
            searchPlaceholder: "योजनाएं खोजें...",

            // --- Voice ---
            voiceTitle: "🎤 वॉइस सहायता",
            voiceSubtitle: "किसानों के लिए कॉल सहायता",
            callNow: "टोल-फ्री नंबर पर कॉल करें",
            availableHours: "24/7 उपलब्ध",
            howIvrWorks: "यह कैसे काम करता है",
            ivrStep1Title: "कॉल करें",
            ivrStep1Desc: "1800-123-4567 डायल करें",
            ivrStep2Title: "भाषा चुनें",
            ivrStep2Desc: "हिंदी चुनें",
            ivrStep3Title: "समस्या बताएं",
            ivrStep3Desc: "लक्षण स्पष्ट रूप से बताएं",
            readyToCall: "मदद चाहिए?",

            // --- Footer ---
            footerAbout: "हमारे बारे में",
            footerAboutText: "किसानों की मदद के लिए AI प्लेटफॉर्म।",
            footerQuickLinks: "लिंक",
            footerContact: "संपर्क",
            footerCopyright: "© 2026 एग्रोविज़न। सर्वाधिकार सुरक्षित।"
        },
        ta: {},
        kn: {},
        mr: {}
    };

    // 2. CORE FUNCTIONS
    
    function setLanguage(lang) {
        const selectedLang = lang || 'en';
        
        // Save to storage
        localStorage.setItem('selectedLanguage', selectedLang);
        
        // Update HTML tag for accessibility
        document.documentElement.lang = selectedLang;
        
        // Update Desktop Selector UI
        const selector = document.getElementById('languageSelect');
        if (selector && Array.from(selector.options).some(option => option.value === selectedLang)) {
            selector.value = selectedLang;
        }
        
        // Update Mobile Selector UI
        const mobileSelector = document.getElementById('languageSelectMobile');
        if (mobileSelector && Array.from(mobileSelector.options).some(option => option.value === selectedLang)) {
            mobileSelector.value = selectedLang;
        }

        // Apply translations
        applyTranslations(selectedLang);
        
        // Dispatch Event for other components
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: selectedLang } }));
    }

    function applyTranslations(lang) {
        const elements = document.querySelectorAll('[data-lang]');
        const langDict = translations[lang] || {};
        
        elements.forEach(element => {
            const key = element.getAttribute('data-lang');
            
            // Logic: Target Lang > English Fallback > Keep Original
            const text = langDict[key] || translations['en'][key];
            
            if (text) {
                // Check if it's an input/textarea placeholder
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.placeholder = text;
                } else {
                    // Regular text content
                    element.textContent = text;
                }
            }
        });
    }

    function init() {
        const savedLang = localStorage.getItem('selectedLanguage') || 'en';
        setLanguage(savedLang);
        
        // Listener for Desktop Selector
        const selector = document.getElementById('languageSelect');
        if (selector) {
            selector.addEventListener('change', (e) => setLanguage(e.target.value));
        }
        
        // Listener for Mobile Selector
        const mobileSelector = document.getElementById('languageSelectMobile');
        if (mobileSelector) {
            mobileSelector.addEventListener('change', (e) => setLanguage(e.target.value));
        }
    }

    // 3. EXPORT PUBLIC API
    return {
        init: init,
        setLanguage: setLanguage,
        get: (key) => {
            const lang = localStorage.getItem('selectedLanguage') || 'en';
            const langDict = translations[lang] || {};
            return langDict[key] || translations['en'][key] || key;
        }
    };

})();

// Initialize on load
document.addEventListener('DOMContentLoaded', AgroVisionLanguage.init);

// Global shortcut for inline HTML onclicks
window.changeLanguage = AgroVisionLanguage.setLanguage;
