//this code creates an alert if there are unsaved form changes
//also creates confirmation alert if delete button clicked
//untested + nonspecific, will only work if only 1 form on page
$(function(){
$(".profileFormWrapperDiv > form input").change(function(){
	someThingChanged = true;
});
$("a").click(function(e){
		if($(this).attr("class") === "deleteButton"){
			return confirm("Are you sure you want to delete this?");
		}else{
				if(someThingChanged==true){
					return confirm("You have unsaved form changes, are you sure you sure to continue?")
				}
		}
});
});
