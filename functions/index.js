const { approveProfessionalAccount, rejectProfessionalAccount } = require("./approve-professional");
const { approvePharmacyRegistration, rejectPharmacyRegistration, respondPharmacyLink } = require("./pharmacy-approval");
exports.approveProfessionalAccount = approveProfessionalAccount;
exports.rejectProfessionalAccount = rejectProfessionalAccount;
exports.approvePharmacyRegistration = approvePharmacyRegistration;
exports.rejectPharmacyRegistration = rejectPharmacyRegistration;
exports.respondPharmacyLink = respondPharmacyLink;
