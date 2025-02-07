document.addEventListener("DOMContentLoaded", function () {
  const addToCartButtons = document.querySelectorAll(".add-to-cart-btn");
  const cartTotalElement = document.querySelector(".cart-total");

  // Initialize cart items array
  let cartItems = [];
  let cartTotal = 0;

  // Event listener for Add to Cart buttons
  addToCartButtons.forEach((button) => {
    button.addEventListener("click", function (event) {
      const productCard = event.target.closest(".product-card");
      const productId = productCard.getAttribute("data-product-id");
      const productName = productCard.querySelector("h3").innerText;
      const productPriceStr = productCard.querySelector("p").innerText;
      const productPrice = parseFloat(productPriceStr.replace("₹", "").trim());

      // Add item to cart array
      cartItems.push({ id: productId, name: productName, price: productPrice });

      // Update cart total
      cartTotal += productPrice;
      cartTotalElement.innerText = `Total: ₹${cartTotal.toFixed(2)}`;

      // Optional: Store cart items in localStorage
      localStorage.setItem("cartItems", JSON.stringify(cartItems));
    });
  });

  // Initialize cart total display
  cartTotalElement.innerText = `Total: ₹${cartTotal.toFixed(2)}`;

  // Optional: Load cart items from localStorage on page load
  const storedCartItems = localStorage.getItem("cartItems");
  if (storedCartItems) {
    cartItems = JSON.parse(storedCartItems);
    cartTotal = cartItems.reduce((total, item) => total + item.price, 0);
    cartTotalElement.innerText = `Total: ₹${cartTotal.toFixed(2)}`;
  }
});
