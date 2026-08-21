const TONE_CLASSES = {
  success: "bg-success",
  warning: "bg-warning text-dark",
  danger: "bg-danger",
  secondary: "bg-secondary",
  light: "bg-light text-dark",
};

export default function Badge({ tone, children }) {
  return <span className={`badge ${TONE_CLASSES[tone] || TONE_CLASSES.light}`}>{children}</span>;
}
