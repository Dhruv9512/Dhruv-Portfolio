from django.shortcuts import render
from .models import Education,Skill,certification_link,Achievements,Work_Experience_and_Internships
# Create your views here.
def about(request):
    # ==============================Education tab===============================
    Education_Data = Education.objects.all()

    # ===========================Skill tab========================
    Skill_All_Data = Skill.objects.all()
    Real_Skill_Data = [];
    name = set() 
    for v in Skill_All_Data:
        if v.Name not in name:  
            Real_Skill_Data.append(Skill.objects.filter(Name=v.Name).all())
            name.add(v.Name)

    # ========================Certifications & Achievements Tab========================
    certification_link_All_Data = certification_link.objects.all()
    Real_certification_link_Data = []
    Achievements_All_Data = Achievements.objects.all()
    Real_Achievements_Data = []

    # Certification list making
    name.clear()
    for v in certification_link_All_Data:
        if v.name not in name:
            Real_certification_link_Data.append(certification_link.objects.filter(name = v.name).all())
            name.add(v.name)
    
    # Achievements list making
    name.clear()
    for v in Achievements_All_Data:
        if v.name not in name:
            Real_Achievements_Data.append(Achievements.objects.filter(name = v.name).all())
            name.add(v.name)
    
    #===================================Work Experience / Internships Tab===================================
    Work_Experience_and_Internships_All_Data = Work_Experience_and_Internships.objects.all()
    Real_Work_Experience_and_Internships_Data = []
    name.clear()
    for v in Work_Experience_and_Internships_All_Data:
        if v.name not in name:
            Real_Work_Experience_and_Internships_Data.append(Work_Experience_and_Internships.objects.filter(name = v.name).all())
            name.add(v.name)
    
    context = {
        "Education":Education_Data,
        "Skill":Real_Skill_Data,
        "Certifications_and_Achievements":{
            "certification_link":Real_certification_link_Data,
            "Achievements":Real_Achievements_Data,
        },
        "Work_Experience_and_Internships":Real_Work_Experience_and_Internships_Data
    }
    return render(request,"about/about.html",context)