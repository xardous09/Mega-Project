function toggleInfoBox() {
    var infoBox = document.getElementById("info_box");
    if (infoBox.style.display === "none" || infoBox.style.display === "") {
        infoBox.style.display = "block";
    } else {
        infoBox.style.display = "none";
    }
}
