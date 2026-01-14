class PaymentModal {
  constructor(bookingId, totalAmount, packageName) {
    this.bookingId = bookingId;
    this.totalAmount = totalAmount;
    this.packageName = packageName;
    window.currentBookingId = bookingId;
  }

  show() {
    const modalHTML = `
            <div class="payment-modal-overlay" id="paymentModalOverlay">
                <div class="payment-modal-container">
                    <div class="payment-header">
                        <h3><i class="fas fa-lock" style="margin-right: 10px;"></i> Secure Payment</h3>
                        <button class="close-payment" onclick="window.paymentModalInstance.hide()">&times;</button>
                    </div>
                    <div class="payment-body">
                        <!-- Order Summary -->
                        <div class="payment-summary">
                            <div class="summary-row">
                                <span style="color: #6c757d; font-weight: 500;">Package</span>
                                <span style="font-weight: 700;">${
                                  this.packageName
                                }</span>
                            </div>
                            <div class="summary-row">
                                <span style="color: #6c757d; font-weight: 500;">Booking ID</span>
                                <span style="font-weight: 700;">#${
                                  this.bookingId
                                }</span>
                            </div>
                            <div class="summary-row summary-total">
                                <span style="font-size: 1.1rem; font-weight: 700;">Total Amount</span>
                                <span style="font-size: 1.3rem; font-weight: 800; color: #28a745;">$${parseFloat(
                                  this.totalAmount
                                ).toFixed(2)}</span>
                            </div>
                        </div>
                        
                        <!-- Payment Form -->
                        <form id="payment-form" class="payment-form">
                            <div class="form-group">
                                <label>Card Number</label>
                                <div style="position: relative;">
                                    <input 
                                        type="text" 
                                        class="card-input" 
                                        id="card-number"
                                        placeholder="1234 5678 9012 3456"
                                        maxlength="19"
                                        required
                                    >
                                    <div style="position: absolute; right: 15px; top: 50%; transform: translateY(-50%); display: flex; gap: 8px;">
                                        <img src="https:
                                        <img src="https:
                                    </div>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label>Cardholder Name</label>
                                <input type="text" id="card-holder" placeholder="JOHN DOE" required>
                            </div>
                            
                            <div class="form-row">
                                <div class="form-col">
                                    <div class="form-group">
                                        <label>Expiry Month</label>
                                        <select id="expiry-month" required>
                                            <option value="">MM</option>
                                            ${Array.from(
                                              { length: 12 },
                                              (_, i) => i + 1
                                            )
                                              .map(
                                                (m) =>
                                                  `<option value="${m
                                                    .toString()
                                                    .padStart(2, "0")}">${m
                                                    .toString()
                                                    .padStart(2, "0")}</option>`
                                              )
                                              .join("")}
                                        </select>
                                    </div>
                                </div>
                                <div class="form-col">
                                    <div class="form-group">
                                        <label>Expiry Year</label>
                                        <select id="expiry-year" required>
                                            <option value="">YY</option>
                                            ${Array.from(
                                              { length: 10 },
                                              (_, i) =>
                                                new Date().getFullYear() + i
                                            )
                                              .map(
                                                (y) =>
                                                  `<option value="${y}">${y
                                                    .toString()
                                                    .slice(-2)}</option>`
                                              )
                                              .join("")}
                                        </select>
                                    </div>
                                </div>
                                <div class="form-col">
                                    <div class="form-group">
                                        <label>CVV</label>
                                        <input type="text" id="cvv" placeholder="123" maxlength="3" required>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="security-note">
                                <i class="fas fa-shield-alt"></i>
                                <strong>Secure SSL Encrypted Payment</strong>
                            </div>
                        </form>
                        
                        <!-- Processing State -->
                        <div id="processing-state" class="processing-state" style="display: none;">
                            <div class="spinner"></div>
                            <h4 style="margin: 0; font-weight: 700;">Verifying Payment...</h4>
                            <p style="color: #6c757d; margin-top: 10px;">Please do not refresh the page</p>
                        </div>
                    </div>
                    <div class="payment-footer" id="payment-footer">
                        <button class="btn-cancel" onclick="window.paymentModalInstance.hide()">Cancel</button>
                        <button class="btn-pay" id="pay-now-primary-btn" onclick="processPayment()">
                            PAY $${parseFloat(this.totalAmount).toFixed(2)}
                        </button>
                    </div>
                </div>
            </div>
        `;

    const existing = document.getElementById("paymentModalOverlay");
    if (existing) existing.remove();

    document.body.insertAdjacentHTML("beforeend", modalHTML);

    window.paymentModalInstance = this;

    const overlay = document.getElementById("paymentModalOverlay");
    overlay.offsetHeight;
    overlay.classList.add("show");

    this.addEventListeners();
  }

  hide() {
    const overlay = document.getElementById("paymentModalOverlay");
    if (overlay) {
      overlay.classList.remove("show");
      setTimeout(() => overlay.remove(), 300);
    }
  }

  addEventListeners() {
    const cardInput = document.getElementById("card-number");
    const cvvInput = document.getElementById("cvv");
    const holderInput = document.getElementById("card-holder");

    if (cardInput) {
      cardInput.addEventListener("input", (e) => {
        let value = e.target.value.replace(/\D/g, "");
        let formattedValue = value.match(/.{1,4}/g)?.join(" ") || value;
        e.target.value = formattedValue;
      });
    }

    if (holderInput) {
      holderInput.addEventListener("input", (e) => {
        e.target.value = e.target.value.toUpperCase();
      });
    }
  }
}

async function processPayment() {
  const form = document.getElementById("payment-form");
  if (!form || !form.checkValidity()) {
    if (form) form.reportValidity();
    return;
  }

  const formElement = document.getElementById("payment-form");
  const processingElement = document.getElementById("processing-state");
  const footerElement = document.getElementById("payment-footer");

  formElement.style.display = "none";
  processingElement.style.display = "block";
  footerElement.style.display = "none";

  const cardNumber = document
    .getElementById("card-number")
    .value.replace(/\s/g, "");
  const cardHolder = document.getElementById("card-holder").value;
  const expiryMonth = document.getElementById("expiry-month").value;
  const expiryYear = document.getElementById("expiry-year").value;
  const cvv = document.getElementById("cvv").value;

  try {
    const bookingId = window.currentBookingId;
    console.log(`Processing payment for booking ${bookingId}`);

    const response = await fetch(`/api/bookings/${bookingId}/pay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_number: cardNumber,
        card_holder: cardHolder,
        expiry_month: expiryMonth,
        expiry_year: expiryYear,
        cvv: cvv,
      }),
    });

    const data = await response.json();

    if (data.success) {
      window.paymentModalInstance.hide();
      setTimeout(() => showPaymentSuccess(data), 350);
    } else {
      alert(data.message || "Payment failed. Please try again.");
      formElement.style.display = "block";
      processingElement.style.display = "none";
      footerElement.style.display = "flex";
    }
  } catch (error) {
    console.error("Payment error:", error);
    alert("Transmission error. Please check your connection.");
    formElement.style.display = "block";
    processingElement.style.display = "none";
    footerElement.style.display = "flex";
  }
}

function showPaymentSuccess(paymentData) {
  const successHTML = `
        <div class="payment-modal-overlay" id="successModalOverlay">
            <div class="payment-modal-container" style="max-width: 500px; text-align: center; padding: 40px 30px;">
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h2 style="margin: 0 0 10px 0; font-weight: 800;">Payment Confirmed!</h2>
                <p style="color: #6c757d; margin-bottom: 30px;">Your booking is successfully paid and verified.</p>
                
                <div style="background: #f8f9ff; padding: 20px; border-radius: 15px; text-align: left; margin-bottom: 30px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.9rem;">
                        <span style="color: #6c757d;">Transaction ID:</span>
                        <strong style="font-family: monospace;">${
                          paymentData.transaction_id
                        }</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.9rem;">
                        <span style="color: #6c757d;">Amount Paid:</span>
                        <strong style="color: #28a745;">$${parseFloat(
                          paymentData.amount
                        ).toFixed(2)}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem;">
                        <span style="color: #6c757d;">Method:</span>
                        <strong>${paymentData.payment_method}</strong>
                    </div>
                </div>
                
                <button onclick="window.location.href='/my-requests'" class="btn-pay" style="width: 100%;">
                    View My Requests
                </button>
            </div>
        </div>
    `;

  const existing = document.getElementById("successModalOverlay");
  if (existing) existing.remove();

  document.body.insertAdjacentHTML("beforeend", successHTML);
  const overlay = document.getElementById("successModalOverlay");
  overlay.offsetHeight;
  overlay.classList.add("show");
}
