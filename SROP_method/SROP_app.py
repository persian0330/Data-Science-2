import torch
import torch.backends.cudnn as cudnn
import numpy as np
import PIL.Image as pil_image
from PIL import ImageFilter
from SROP_method.model import SROP
from SROP_method.offset_map import Offs_Pro
from SROP_method.fusion import img_fusion
from SRCNN_method.SRCNN_app import get_srcnn
from utils import tensor2img

def get_srop(image_file_dir, scale):
    
    if scale==2:
        weights_file='SROP_method/train_results/SROP_x2.pth'
    elif scale==3:
        weights_file='SROP_method/train_results/SROP_x3.pth'
    elif scale==4:
        weights_file='SROP_method/train_results/SROP_x4.pth'
        
    cudnn.benchmark = True
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    model=SROP(num_channels=3,scale=scale).to(device)
    Mapping_Offset=Offs_Pro().to(device)
    image = pil_image.open(image_file_dir).convert('RGB')
    state_dict = model.state_dict()
    for n, p in torch.load(weights_file, map_location=lambda storage, loc: storage).items():
        if n in state_dict.keys():
            state_dict[n].copy_(p)
        else:
            raise KeyError(n)

    model.eval()
    with torch.no_grad():
        lr = image
        #lr=lr.filter(ImageFilter.SHARPEN)
        #hr_width=image.width * scale
        #hr_height=image.height * scale
        #sr_flat = lr.resize((hr_width, hr_height), resample=pil_image.LANCZOS)
        sr_flat=get_srcnn(image_file_dir, scale)
        sr_flat=np.array(sr_flat).astype(np.float32)
            # sr_flat is a nparray of size (sh,sw,3)
        sr_flat=torch.from_numpy(sr_flat).unsqueeze(0).permute(0,3,1,2)
            # sr_flat is a tensor of size (1,3,sh,sw) 
        lr_image = np.array(lr).astype(np.float32)
            # lr_image is a nparray of size (h,w,3)
        lr_image=torch.from_numpy(lr_image).unsqueeze(0).permute(0,3,1,2)
            # lr_image is a tensor of size (1,3,h,w)             
        sr_flat=sr_flat.to(device)
        lr_image=lr_image.to(device)
        offset_map = model(lr_image).clamp(-1,1)
            # offset_map is of size (1,2,sh,sw) 
        sr_offset=Mapping_Offset(lr_image,offset_map,scale,Train=False)
            # sr_offset is of size (1,3,sh,sw)
        sr_result=img_fusion(sr_flat, sr_offset, offset_map)
            # sr_result is of size (1,3,sh,sw)
        sr_img=tensor2img(sr_result)
        
    return sr_img