/** Dados públicos da organização (definidos na Vercel; valores padrão para desenvolvimento). */
export const site = {
  orgName:
    process.env.NEXT_PUBLIC_ORG_NAME || "Igreja organizadora do CANTEMOS",
  contactEmail: process.env.NEXT_PUBLIC_CONTACT_EMAIL || "",
  updatedAt: "02/11/2026",
};
