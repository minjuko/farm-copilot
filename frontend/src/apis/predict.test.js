import { instance } from "./instance";
import { uploadImage } from "./predict";

jest.mock("./instance", () => ({
  instance: { post: jest.fn() },
}));

test("uploads the image multipart field without overriding the browser boundary", () => {
  const image = new File(["image"], "crop.jpg", { type: "image/jpeg" });
  uploadImage(image);

  expect(instance.post).toHaveBeenCalledTimes(1);
  const [url, formData, config] = instance.post.mock.calls[0];
  expect(url).toBe("/detect/upload/");
  expect(formData.get("image")).toBe(image);
  expect(config).toEqual({ headers: { "Content-Type": undefined } });
});
