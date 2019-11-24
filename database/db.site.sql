-- When a new site is inserted, also insert a corresponding manual program for it

DROP FUNCTION IF EXISTS site_insert_manual_program CASCADE;
CREATE FUNCTION site_insert_manual_program()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	INSERT INTO public.program (site,name,label,onOff,priority,qManual,qHide,action,
		nDays, refDate,
		startMode,startTime,
		stopMode,endTime) VALUES
		(
			NEW.id,  -- site id
			'Manual ' || NEW.name, -- program name
			'Manual', -- program label
			(SELECT id FROM public.webList WHERE grp='onOff' AND key='on'), -- onOff
			-1, -- priority
			true, -- qManual
			true, -- qHide
			(SELECT id FROM public.webList WHERE grp='evAct' AND key='nDays'), -- action
			1, -- nDays i.e. every day
			CURRENT_DATE, -- refDate
			(SELECT id FROM public.webList WHERE grp='evCel' AND key='dawn'), -- mode
			'13:00:00', -- startTime -> 11 hours before dawn
			(SELECT id FROM public.webList WHERE grp='evCel' AND key='dusk'), -- mode
			'11:00:00' -- endTIme -> 11 hours after dusk
		);
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS site_insert ON site;
CREATE TRIGGER site_insert
	AFTER INSERT ON site
	FOR EACH ROW
	EXECUTE FUNCTION site_insert_manual_program();
