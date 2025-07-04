// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY || "AIzaSyDtbqyo_2B3wGU327yxDXhxF1qrTc_E_vM",
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN || "clinicaltrialshub-6a7a3.firebaseapp.com",
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID || "clinicaltrialshub-6a7a3",
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET || "clinicaltrialshub-6a7a3.firebasestorage.app",
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID || "710663666895",
  appId: process.env.REACT_APP_FIREBASE_APP_ID || "1:710663666895:web:126df64aca25ddd98b0bba",
  measurementId: process.env.REACT_APP_FIREBASE_MEASUREMENT_ID || "G-RJ69TB6RX6"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);