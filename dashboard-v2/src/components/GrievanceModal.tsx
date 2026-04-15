import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertTriangle, Send, Loader2, Check } from "lucide-react";
import { useWallet } from "../hooks/useWallet";
import { useToast } from "../hooks/useToast";
import api from "../lib/api";

interface Fiduciary {
  id: string;
  name: string;
  registration_number: string;
}

interface GrievanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  consentId?: string;
  fiduciaryId?: string;
  onSuccess?: () => void;
}

const GRIEVANCE_TYPES = [
  {
    value: "ACCESS",
    label: "Data Access Request",
    desc: "Request access to your personal data",
  },
  {
    value: "CORRECTION",
    label: "Data Correction",
    desc: "Request correction of inaccurate data",
  },
  {
    value: "DELETION",
    label: "Data Deletion",
    desc: "Request deletion of your personal data",
  },
  {
    value: "OBJECTION",
    label: "Objection to Processing",
    desc: "Object to processing of your data",
  },
  {
    value: "PORTABILITY",
    label: "Data Portability",
    desc: "Request data in portable format",
  },
  {
    value: "UNLAWFUL_PROCESSING",
    label: "Unlawful Processing",
    desc: "Report unauthorized data processing",
  },
  {
    value: "BREACH_NOTIFICATION",
    label: "Data Breach",
    desc: "Report a data breach incident",
  },
  { value: "OTHER", label: "Other", desc: "Other grievance or complaint" },
];

export default function GrievanceModal({
  isOpen,
  onClose,
  consentId,
  fiduciaryId,
  onSuccess,
}: GrievanceModalProps) {
  const { address } = useWallet();
  const { success, error } = useToast();
  const [fiduciaries, setFiduciaries] = useState<Fiduciary[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const [formData, setFormData] = useState({
    fiduciary_id: fiduciaryId || "",
    grievance_type: "",
    subject: "",
    description: "",
    consent_id: consentId || "",
  });

  useEffect(() => {
    if (isOpen) {
      loadFiduciaries();
    }
  }, [isOpen]);

  useEffect(() => {
    if (fiduciaryId) {
      setFormData((prev) => ({ ...prev, fiduciary_id: fiduciaryId }));
    }
    if (consentId) {
      setFormData((prev) => ({ ...prev, consent_id: consentId }));
    }
  }, [fiduciaryId, consentId]);

  async function loadFiduciaries() {
    try {
      const response = await api.get("/api/v1/public/fiduciaries");
      setFiduciaries(response.data?.data?.fiduciaries || []);
    } catch (err) {
      console.error("Failed to load fiduciaries:", err);
    }
  }

  async function handleSubmit() {
    if (!address) {
      error("Wallet Not Connected", "Please connect your wallet first");
      return;
    }

    if (!formData.fiduciary_id) {
      error("Missing Fiduciary", "Please select a fiduciary");
      return;
    }

    if (!formData.grievance_type) {
      error("Missing Type", "Please select a grievance type");
      return;
    }

    if (formData.subject.length < 10) {
      error("Subject Too Short", "Subject must be at least 10 characters");
      return;
    }

    if (formData.description.length < 50) {
      error(
        "Description Too Short",
        "Description must be at least 50 characters",
      );
      return;
    }

    setLoading(true);

    try {
      const response = await api.post("/api/v1/public/grievance/submit", {
        principal_wallet: address,
        fiduciary_id: formData.fiduciary_id,
        grievance_type: formData.grievance_type,
        subject: formData.subject,
        description: formData.description,
        consent_id: formData.consent_id || null,
      });

      if (response.data.success) {
        setSubmitted(true);
        success("Grievance Submitted", "Your grievance has been recorded");
        setTimeout(() => {
          onSuccess?.();
          handleClose();
        }, 2000);
      }
    } catch (err: any) {
      error(
        "Submission Failed",
        err.response?.data?.detail || "Failed to submit grievance",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleClose() {
    onClose();
    setTimeout(() => {
      setSubmitted(false);
      setFormData({
        fiduciary_id: fiduciaryId || "",
        grievance_type: "",
        subject: "",
        description: "",
        consent_id: consentId || "",
      });
    }, 300);
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={styles.overlay}
          onClick={handleClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            style={styles.modal}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={styles.header}>
              <div style={styles.headerIcon}>
                <AlertTriangle size={24} color="#f59e0b" />
              </div>
              <div>
                <h2 style={styles.title}>Submit Grievance</h2>
                <p style={styles.subtitle}>
                  File a complaint under DPDP Act Section 13
                </p>
              </div>
              <motion.button
                onClick={handleClose}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                style={styles.closeBtn}
              >
                <X size={18} />
              </motion.button>
            </div>

            <div style={styles.content}>
              {submitted ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  style={styles.successContent}
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", delay: 0.2 }}
                    style={styles.successIcon}
                  >
                    <Check size={40} />
                  </motion.div>
                  <h3 style={styles.successTitle}>Grievance Submitted!</h3>
                  <p style={styles.successText}>
                    Your grievance has been recorded. The fiduciary must
                    acknowledge within 24 hours and resolve within 30 days as
                    per DPDP Act guidelines.
                  </p>
                </motion.div>
              ) : (
                <>
                  <label style={styles.label}>Select Fiduciary</label>
                  <select
                    value={formData.fiduciary_id}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        fiduciary_id: e.target.value,
                      }))
                    }
                    style={styles.select}
                  >
                    <option value="">Choose a fiduciary...</option>
                    {fiduciaries.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.registration_number})
                      </option>
                    ))}
                  </select>

                  <label style={styles.label}>Grievance Type</label>
                  <div style={styles.typeGrid}>
                    {GRIEVANCE_TYPES.map((type) => (
                      <motion.div
                        key={type.value}
                        onClick={() =>
                          setFormData((prev) => ({
                            ...prev,
                            grievance_type: type.value,
                          }))
                        }
                        whileHover={{ scale: 1.01 }}
                        style={{
                          ...styles.typeCard,
                          ...(formData.grievance_type === type.value
                            ? styles.typeCardActive
                            : {}),
                        }}
                      >
                        <div style={styles.typeLabel}>{type.label}</div>
                        <div style={styles.typeDesc}>{type.desc}</div>
                      </motion.div>
                    ))}
                  </div>

                  {formData.grievance_type === "BREACH_NOTIFICATION" && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      style={styles.warningBox}
                    >
                      <AlertTriangle size={16} />
                      Breach notifications are marked as URGENT priority for
                      immediate action.
                    </motion.div>
                  )}

                  <label style={styles.label}>Subject</label>
                  <input
                    type="text"
                    placeholder="Brief summary of your grievance..."
                    value={formData.subject}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        subject: e.target.value,
                      }))
                    }
                    style={styles.input}
                    maxLength={255}
                  />
                  <div style={styles.charCount}>
                    {formData.subject.length}/255
                  </div>

                  <label style={styles.label}>Description</label>
                  <textarea
                    placeholder="Provide detailed description of your grievance (minimum 50 characters)..."
                    value={formData.description}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                    style={styles.textarea}
                    rows={5}
                  />
                  <div style={styles.charCount}>
                    {formData.description.length}/2000 (min 50)
                  </div>

                  {consentId && (
                    <div style={styles.infoBox}>
                      This grievance is related to consent:{" "}
                      {consentId.slice(0, 8)}...
                    </div>
                  )}
                </>
              )}
            </div>

            {!submitted && (
              <div style={styles.footer}>
                <motion.button
                  onClick={handleClose}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  style={styles.cancelBtn}
                >
                  Cancel
                </motion.button>
                <motion.button
                  onClick={handleSubmit}
                  disabled={loading}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  style={styles.submitBtn}
                >
                  {loading ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{
                        duration: 1,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    >
                      <Loader2 size={16} />
                    </motion.div>
                  ) : (
                    <Send size={16} />
                  )}
                  Submit Grievance
                </motion.button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(11,9,23,0.85)",
    backdropFilter: "blur(8px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    padding: 20,
  },
  modal: {
    background: "linear-gradient(180deg, #1a1429 0%, #0b0917 100%)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 24,
    width: "100%",
    maxWidth: 560,
    maxHeight: "90vh",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    display: "flex",
    alignItems: "flex-start",
    gap: 16,
    padding: "24px 24px 16px",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
  },
  headerIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    background: "rgba(245,158,11,0.1)",
    border: "1px solid rgba(245,158,11,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 20,
    fontWeight: 700,
    color: "#ede9ff",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 12,
    color: "#5a5480",
  },
  closeBtn: {
    marginLeft: "auto",
    padding: 8,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#9d96c8",
    cursor: "pointer",
  },
  content: {
    flex: 1,
    overflow: "auto",
    padding: 24,
  },
  label: {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    color: "#ede9ff",
    marginBottom: 8,
    marginTop: 16,
  },
  select: {
    width: "100%",
    padding: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#ede9ff",
    fontSize: 14,
    outline: "none",
    cursor: "pointer",
  },
  typeGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 8,
    marginTop: 8,
  },
  typeCard: {
    padding: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  typeCardActive: {
    background: "rgba(245,158,11,0.1)",
    borderColor: "rgba(245,158,11,0.3)",
  },
  typeLabel: {
    fontWeight: 600,
    color: "#ede9ff",
    fontSize: 12,
    marginBottom: 2,
  },
  typeDesc: {
    fontSize: 10,
    color: "#5a5480",
    lineHeight: 1.3,
  },
  warningBox: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: 12,
    background: "rgba(244,63,94,0.1)",
    border: "1px solid rgba(244,63,94,0.2)",
    borderRadius: 10,
    color: "#fb7185",
    fontSize: 12,
    marginTop: 12,
  },
  input: {
    width: "100%",
    padding: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#ede9ff",
    fontSize: 14,
    outline: "none",
  },
  textarea: {
    width: "100%",
    padding: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#ede9ff",
    fontSize: 14,
    outline: "none",
    resize: "vertical",
    minHeight: 100,
  },
  charCount: {
    textAlign: "right",
    fontSize: 10,
    color: "#5a5480",
    marginTop: 4,
  },
  infoBox: {
    padding: 12,
    background: "rgba(59,130,246,0.1)",
    border: "1px solid rgba(59,130,246,0.2)",
    borderRadius: 10,
    color: "#60a5fa",
    fontSize: 12,
    marginTop: 16,
  },
  footer: {
    display: "flex",
    gap: 8,
    padding: "16px 24px",
    borderTop: "1px solid rgba(255,255,255,0.05)",
  },
  cancelBtn: {
    padding: "12px 20px",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#9d96c8",
    fontWeight: 600,
    fontSize: 13,
    cursor: "pointer",
  },
  submitBtn: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: "12px 20px",
    background: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    border: "none",
    borderRadius: 10,
    color: "#0b0917",
    fontWeight: 600,
    fontSize: 13,
    cursor: "pointer",
  },
  successContent: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px 20px",
    textAlign: "center",
  },
  successIcon: {
    width: 80,
    height: 80,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #10b981, #34d399)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "white",
    marginBottom: 20,
  },
  successTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 22,
    fontWeight: 700,
    color: "#ede9ff",
    marginBottom: 8,
  },
  successText: {
    fontSize: 13,
    color: "#5a5480",
    maxWidth: 300,
    lineHeight: 1.6,
  },
};
