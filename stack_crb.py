import getpass
from nipype.interfaces import fsl
import os
import csv

user=getpass.getuser()
template_stack = os.path.abspath("./res/template_T2.nii.gz")
CRB_BRAIN = os.path.abspath("./res/CRB_BRAIN_Template.nii.gz")
CRB_TEMPLATE = os.path.abspath("./res/CRB_Template.nii.gz")

RCRB=18 #higher value
LCRB=17 #lower value


class CRB_PREP(object):

    def __init__(self, parent_dir, orig_brain, man_seg, PCA, STACK):
        self.parent_dir = parent_dir
        self.orig_brain = orig_brain
        self.man_seg = man_seg
        self.PCA = PCA
        self.stack = STACK

        os.chdir(parent_dir)

    def reg_brain(self):

        if self.PCA >= 44:
            self.outmatrix_crb = os.path.join(self.parent_dir,'reg_to_CRB_template.mat')
            flt = fsl.FLIRT()
            flt.inputs.in_file =  self.orig_brain
            flt.inputs.reference = CRB_BRAIN
            flt.inputs.out_matrix_file = self.outmatrix_crb
            flt.inputs.out_file = os.path.join(self.parent_dir,'reg_to_CRB_template.nii.gz')
            print(flt.cmdline)
            flt.run()

            #apply reg to segmentation

            app = fsl.FLIRT()
            app.inputs.in_file = self.man_seg
            app.inputs.reference = self.get_template()
            app.inputs.apply_xfm = True
            app.inputs.in_matrix_file =  self.outmatrix_crb
            app.inputs.interp = 'nearestneighbour'
            app.inputs.out_file = os.path.join(self.parent_dir ,'manual_seg_reg_to_CRB_template.nii.gz')
            print(app.cmdline)
            app.run()

        else:
            #REG TO BEST PCA MATCH FIRST

            self.outmatrix_pca = os.path.join(self.parent_dir,'reg_to_PCA_template.mat')
            flt_pca = fsl.FLIRT()
            flt_pca.inputs.in_file =  self.orig_brain
            flt_pca.inputs.reference = self.get_template()
            flt_pca.inputs.out_matrix_file = self.outmatrix_pca
            flt_pca.inputs.out_file = os.path.join(self.parent_dir , 'reg_to_PCA_template.nii.gz')
            print(flt_pca.cmdline)
            flt_pca.run()

            #apply reg to segmentation

            app_pca = fsl.FLIRT()
            app_pca.inputs.in_file = self.man_seg
            app_pca.inputs.reference = self.get_template()
            app_pca.inputs.apply_xfm = True
            app_pca.inputs.in_matrix_file =  self.outmatrix_pca
            app_pca.inputs.interp = 'nearestneighbour'
            app_pca.inputs.out_file = os.path.join(self.parent_dir,'manual_seg_reg_to_PCA_template.nii.gz')
            print(app_pca.cmdline)
            app_pca.run()

            #REG PCA REG TO OLDEST

            self.outmatrix_CRB = os.path.join(self.parent_dir,'reg_to_CRB_template.mat')
            flt_crb = fsl.FLIRT()
            flt_crb.inputs.in_file =  os.path.join(self.parent_dir,'reg_to_PCA_template.nii.gz')
            flt_crb.inputs.reference =  CRB_BRAIN
            flt_crb.inputs.out_matrix_file = self.outmatrix_CRB
            flt_crb.inputs.out_file = os.path.join(self.parent_dir, 'reg_to_CRB_template.nii.gz')
            print(flt_crb.cmdline)
            flt_crb.run()

            #apply reg to segmentation

            app_crb = fsl.FLIRT()
            app_crb.inputs.in_file = os.path.join(self.parent_dir, 'manual_seg_reg_to_PCA_template.nii.gz')
            app_crb.inputs.reference = CRB_BRAIN
            app_crb.inputs.apply_xfm = True
            app_crb.inputs.in_matrix_file =  self.outmatrix_CRB
            app_crb.inputs.interp = 'nearestneighbour'
            app_crb.inputs.out_file = os.path.join(self.parent_dir, 'manual_seg_reg_to_CRB_template.nii.gz')
            print(app_crb.cmdline)
            app_crb.run()


    def get_index(self):
        if self.PCA >= 44:
            return 16
        elif self.PCA <= 28:
            return 0
        else:
            return self.PCA - 28

    def get_template(self):
        outfile_nii = os.path.join(self.parent_dir,'pca_template.nii.gz')
        fslroi = fsl.ExtractROI(in_file=template_stack,
                            roi_file=outfile_nii,
                            t_min=self.get_index(),
                            t_size=1)
        fslroi.run()
        return os.path.join(self.parent_dir,'pca_template.nii.gz')


    def reg_crb(self):

        get_crb = fsl.ImageMaths()
        get_crb.inputs.op_string = '-thr {0:.1f} -uthr {1:.1f}'.format(LCRB-0.5,RCRB+0.5)
        get_crb.inputs.in_file = os.path.join(self.parent_dir , 'manual_seg_reg_to_CRB_template.nii.gz')
        get_crb.inputs.out_file = os.path.join(self.parent_dir , 'extracted_CRB.nii.gz')
        print(get_crb.cmdline)
        get_crb.run()


        flt_crb = fsl.FLIRT()
        flt_crb.inputs.in_file =  os.path.join(self.parent_dir , 'extracted_CRB.nii.gz')
        flt_crb.inputs.reference =  CRB_TEMPLATE
        flt_crb.inputs.out_file = os.path.join(self.parent_dir , 'registered_extracted_CRB.nii.gz')
        print(flt_crb.cmdline)
        flt_crb.run()

    def add_to_stack(self):
        if os.path.isfile(self.stack):
            stack = self.stack
        else:
            stack = CRB_TEMPLATE
        merger = fsl.Merge()
        merger.inputs.in_files = [stack,
                                  os.path.join(self.parent_dir , 'registered_extracted_CRB.nii.gz')]
        merger.inputs.dimension = 't'
        merger.inputs.merged_file = self.stack
        print(merger.cmdline)
        merger.run()

    def bin_crop(self, final_image, xmin, xsize,
                                    ymin, ysize,
                                    zmin, zsize,
                                    tmin, tsize):
        cropper = fsl.ExtractROI()
        cropper.inputs.in_file = self.stack
        cropper.inputs.x_min = xmin
        cropper.inputs.x_size = xsize
        cropper.inputs.y_min = ymin
        cropper.inputs.y_size = ysize
        cropper.inputs.z_min = zmin
        cropper.inputs.z_size = zsize
        cropper.inputs.t_min = tmin
        cropper.inputs.t_size = tsize
        cropper.inputs.roi_file = final_image
        print(cropper.cmdline)
        cropper.run()


        binner = fsl.ImageMaths(in_file = final_image,
                                out_file = final_image,
                                op_string = '-bin')
        print(binner.cmdline)
        binner.run()



if __name__ == '__main__':

    in_file = '/home/pirc/PIRC1-Storage/processing/Neonatal_Segmentation/CRB_BDS_GOOD_20170324.csv'
    STACK = '/home/pirc/PIRC1-Storage/processing/Neonatal_Segmentation/Stacked_CRB_20170324.nii.gz'
    FINAL = '/home/pirc/PIRC1-Storage/processing/Neonatal_Segmentation/Stacked_CRB_CROP_BIN_20170324.nii.gz'
##### IN CASE YOU ARE CREATING IT FROM SCRATCH:
#    if os.path.isfile(STACK):
#        os.remove(STACK)

    with open(in_file, 'rb') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            print(row['Parent_Dir'])
            parent_dir = row['Parent_Dir']
            orig_brain = row['T2']
            man_seg = row['Segmentation']
            PCA = row['PCA']
            SCORE = row['CRB_DYSP']
            prep = CRB_PREP(parent_dir, orig_brain, man_seg, PCA, STACK)
#            prep.reg_brain()
#            prep.reg_crb()
#            prep.add_to_stack()
        prep.bin_crop(FINAL, 9, 100, 0, 90, 0, 70, 1, -1)


