import numpy as np
import SimpleITK as sitk
import torch
import torch.nn as nn
from medpy import metric
from scipy.ndimage import zoom


def calculate_metric_percase(pred, gt):
    pred[pred > 0] = 1
    gt[gt > 0] = 1
    if pred.sum() > 0 and gt.sum() > 0:
        dice = metric.binary.dc(pred, gt)
        hd95 = metric.binary.hd95(pred, gt)
        return dice, hd95
    elif pred.sum() > 0 and gt.sum() == 0:
        return 1, 0
    else:
        return 0, 0


def test_single_image(
    image,
    label,
    net,
    classes,
    patch_size=[256, 256],
    test_save_path=None,
    case=None,
    z_spacing=1,
):
    image, label = image.float(), label.squeeze(0).cpu().detach().numpy()
    net.eval()
    with torch.no_grad():
        print("input shape", image.shape)
        output = net(image)
        print("output shape", output.shape)
        # softmax = torch.softmax(output, dim=1)
        # argmax = torch.argmax(softmax, dim=1, keepdim=True)
        argmax = torch.argmax(torch.softmax(output, dim=1), dim=1).squeeze(0)
        prediction = argmax.cpu().detach().numpy()
        # print(argmax.shape)
        # prediction = argmax.cpu().detach()
        return prediction
    """ metric_list = []
    for i in range(1, classes):
        metric_list.append(calculate_metric_percase(prediction == i, label == i))

    if test_save_path is not None:
        img_itk = sitk.GetImageFromArray(image.astype(np.float32))
        prd_itk = sitk.GetImageFromArray(prediction.astype(np.float32))
        lab_itk = sitk.GetImageFromArray(label.astype(np.float32))
        img_itk.SetSpacing((1, 1, z_spacing))
        prd_itk.SetSpacing((1, 1, z_spacing))
        lab_itk.SetSpacing((1, 1, z_spacing))
        sitk.WriteImage(prd_itk, test_save_path + '/'+case + "_pred.nii.gz")
        sitk.WriteImage(img_itk, test_save_path + '/'+ case + "_img.nii.gz")
        sitk.WriteImage(lab_itk, test_save_path + '/'+ case + "_gt.nii.gz")
    return metric_list """


def test_single_volume(
    image,
    label,
    net,
    classes,
    patch_size=[224, 224],
    test_save_path=None,
    case=None,
    z_spacing=1,
):
    image, label = (
        image.squeeze(0).cpu().detach().numpy(),
        label.squeeze(0).cpu().detach().numpy(),
    )
    if len(image.shape) == 3:
        prediction = np.zeros_like(label)
        for ind in range(image.shape[0]):
            slice = image[ind, :, :]
            x, y = slice.shape[0], slice.shape[1]
            if x != patch_size[0] or y != patch_size[1]:
                slice = zoom(
                    slice, (patch_size[0] / x, patch_size[1] / y), order=3
                )  # previous using 0
            input = torch.from_numpy(slice).unsqueeze(0).unsqueeze(0).float().cuda()
            net.eval()
            with torch.no_grad():
                # print("input.shape", input.shape)
                outputs = net(input)
                out = torch.argmax(torch.softmax(outputs, dim=1), dim=1).squeeze(0)
                out = out.cpu().detach().numpy()
                if x != patch_size[0] or y != patch_size[1]:
                    pred = zoom(out, (x / patch_size[0], y / patch_size[1]), order=0)
                else:
                    pred = out
                # print("pred.shape", pred.shape)
                prediction[ind] = pred
    else:
        input = torch.from_numpy(image).unsqueeze(0).unsqueeze(0).float().cuda()
        net.eval()
        with torch.no_grad():
            out = torch.argmax(torch.softmax(net(input), dim=1), dim=1).squeeze(0)
            prediction = out.cpu().detach().numpy()
    metric_list = []
    # print(prediction.shape)
    for i in range(1, classes + 1):
        metric_list.append(calculate_metric_percase(prediction == i, label == i))

    if test_save_path is not None:
        img_itk = sitk.GetImageFromArray(image.astype(np.float32))
        prd_itk = sitk.GetImageFromArray(prediction.astype(np.float32))
        lab_itk = sitk.GetImageFromArray(label.astype(np.float32))
        img_itk.SetSpacing((1, 1, z_spacing))
        prd_itk.SetSpacing((1, 1, z_spacing))
        lab_itk.SetSpacing((1, 1, z_spacing))
        sitk.WriteImage(prd_itk, test_save_path + "/" + case + "_pred.nii.gz")
        sitk.WriteImage(img_itk, test_save_path + "/" + case + "_img.nii.gz")
        sitk.WriteImage(lab_itk, test_save_path + "/" + case + "_gt.nii.gz")
    return metric_list, torch.from_numpy(prediction)
