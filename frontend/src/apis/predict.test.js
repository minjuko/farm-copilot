import { instance } from "./instance";
import { searchSoilAddresses, uploadImage } from "./predict";

jest.mock("./instance", () => ({
  instance: { get: jest.fn(), post: jest.fn() },
}));

test("uploads the image multipart field without overriding the browser boundary", () => {
  const image = new File(["image"], "crop.jpg", { type: "image/jpeg" });
  uploadImage(image);

  expect(instance.post).toHaveBeenCalledTimes(1);
  const [url, formData] = instance.post.mock.calls[0];
  expect(url).toBe("/detect/upload/");
  expect(formData.get("image")).toBe(image);
  expect(instance.post).toHaveBeenCalledWith("/detect/upload/", formData);
});

test("sends soil requests as JSON objects through the shared instance", () => {
  const { getSoilExamData, getSoilFertilizerInfo } = require("./predict");
  getSoilExamData("고추", "전주시");
  getSoilFertilizerInfo({ soil_data: { acid: 6.5 } });

  expect(instance.post).toHaveBeenCalledWith("/soil/soil_exam/", {
    crop_name: "고추",
    address: "전주시",
  });
  expect(instance.post).toHaveBeenCalledWith("/soil/get-soil-fertilizer-info/", {
    soil_data: { acid: 6.5 },
  });
});

test("searches standardized soil addresses through the backend", () => {
  searchSoilAddresses("전라북도 전주시");
  expect(instance.get).toHaveBeenCalledWith("/soil/address-search/", {
    params: { query: "전라북도 전주시" },
  });
});
